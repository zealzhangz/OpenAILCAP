"""B5 narrow capability-gated public tool broker over *existing* B2+B4 engines.

The broker accepts opaque test principals and strictly checked JSON commands.
The browser uses B2 sessions/CSRF. Untrusted bearer principals do NOT get
direct B2 v2 access through this server: only v3 tools receive their bearer.
This is NOT a kernel rewrite or OS/plugin sandbox. Trusted host code still
directly invokes B2/B4 and SQLite remains a potential privileged bypass.
"""
from __future__ import annotations
import json
import re
import time
from dataclasses import dataclass
from http.server import ThreadingHTTPServer
from urllib.parse import urlsplit,unquote,parse_qs
from schema_core import Rejected,SchemaStore
from schema_http import handler_for
from policy import validate_source,RuleError
from registry import ExtensionRegistry

TOOLS={
    "metadata.upsert","app.publish","app.rollback",
    "code.verify","code.stage","code.publish","code.rollback",
    "release.read","risk.score"
}

@dataclass(frozen=True)
class Grant:
    actor: object
    tools: frozenset[str]
    expires_at: float

class ToolBroker:
    def __init__(self,store:SchemaStore,registry:ExtensionRegistry):
        self.store=store
        self.registry=registry
        self.grants={}
    def grant(self,token,actor,tools,ttl_seconds=3600):
        if not isinstance(token,str) or len(token)<20:
            raise ValueError("random token required")
        if not isinstance(tools,(set,frozenset)) or not set(tools)<=TOOLS:
            raise ValueError("invalid tools")
        self.grants[token]=Grant(actor,frozenset(tools),time.time()+ttl_seconds)
    def revoke(self,token):
        self.grants.pop(token,None)
    def authorize(self,token,app,tool):
        grant=self.grants.get(token)
        if not grant or time.time()>grant.expires_at or not grant.actor.active:
            raise Rejected(401,"TOOL_GRANT_EXPIRED_OR_REVOKED")
        SchemaStore.authorize(grant.actor,app)
        if tool not in grant.tools:
            raise Rejected(403,"TOOL_NOT_GRANTED")
        return grant.actor
    @staticmethod
    def _shape(args,keys):
        if not isinstance(args,dict) or set(args)!=set(keys):
            raise Rejected(422,"TOOL_ARGUMENTS_INVALID")
    def call(self,token,app,tool,args):
        actor=self.authorize(token,app,tool)
        if tool=="metadata.upsert":
            self._shape(args,("command",))
            return self.store.mutate(actor,app,args["command"])
        if tool=="app.publish":
            self._shape(args,("command",))
            return self.store.publish(actor,app,args["command"])
        if tool=="app.rollback":
            self._shape(args,("command",))
            return self.store.rollback(actor,app,args["command"])
        if tool=="code.verify":
            self._shape(args,("source",))
            try:
                checked=validate_source(args["source"])
                proof=self.registry.sandbox.test(checked["source"])
            except RuleError as e:
                raise Rejected(422,e.code) from None
            # No reusable SandboxProof handed to untrusted caller.
            return {"decision":"VERIFIED","sourceHash":proof.source_hash,
                    "cases":proof.cases,"stageAuthorized":False}
        if tool=="code.stage":
            self._shape(args,("source",))
            SchemaStore.authorize(actor,app,publish=True)
            try:
                checked=validate_source(args["source"])
                proof=self.registry.sandbox.test(checked["source"])
            except RuleError as e:
                raise Rejected(422,e.code) from None
            return self.registry.stage(actor,app,args["source"],proof)
        if tool=="code.publish":
            self._shape(args,("artifactHash","expectedExtensionVersion"))
            return self.registry.publish(actor,app,args["artifactHash"],
                                         args["expectedExtensionVersion"])
        if tool=="code.rollback":
            self._shape(args,("expectedExtensionVersion","targetVersion"))
            return self.registry.rollback(actor,app,args["expectedExtensionVersion"],
                                          args["targetVersion"])
        if tool=="release.read":
            self._shape(args,())
            return self.store.release(actor,app)
        if tool=="risk.score":
            self._shape(args,("recordId","supplierScore","monthsActive"))
            if not isinstance(args["recordId"],str):
                raise Rejected(422,"TOOL_ARGUMENTS_INVALID")
            try:
                return self.registry.score_record(
                    actor,app,args["recordId"],
                    args["supplierScore"],args["monthsActive"])
            except RuleError as e:
                raise Rejected(422,e.code) from None
        raise Rejected(404,"TOOL_NOT_FOUND")

def make_server(store,registry,broker,sessions,human,password):
    # Explicit empty v2 bearer map. Human editor receives server-side session.
    Parent=handler_for(store,{},sessions,human,password)
    class Handler(Parent):
        def _tool_target(self):
            parts=[unquote(x) for x in urlsplit(self.path).path.split("/") if x]
            if len(parts)==5 and parts[:2]==["v3","apps"] and parts[3]=="tools":
                return parts[2],parts[4]
            return None
        def do_POST(self):
            target=self._tool_target()
            if target is None:
                return super().do_POST()
            try:
                auth=self.headers.get("Authorization","")
                token=auth[7:] if auth.startswith("Bearer ") else ""
                args=self._body()
                app,tool=target
                result=broker.call(token,app,tool,args)
                self._json(200,result)
            except Rejected as e:
                self._json(e.status,{"error":e.code})
            except Exception:
                self._json(503,{"error":"TOOL_EXECUTION_UNAVAILABLE"})
        def do_GET(self):
            parts=[unquote(x) for x in urlsplit(self.path).path.split("/") if x]
            if len(parts)==4 and parts[:2]==["v3","apps"] and parts[3]=="capabilities":
                try:
                    auth=self.headers.get("Authorization","")
                    token=auth[7:] if auth.startswith("Bearer ") else ""
                    # Authorize discovery via any known (active) tool grant.
                    grant=broker.grants.get(token)
                    if not grant or time.time()>grant.expires_at or not grant.actor.active:
                        raise Rejected(401,"TOOL_GRANT_EXPIRED_OR_REVOKED")
                    SchemaStore.authorize(grant.actor,parts[2])
                    self._json(200,{"tools":sorted(grant.tools),
                                    "subject":grant.actor.name,
                                    "app":grant.actor.app})
                except Rejected as e:
                    self._json(e.status,{"error":e.code})
                return
            # Risk browser session endpoint with no client-provided code.
            if len(parts)==7 and parts[:2]==["v2","apps"] and (
                parts[3:6]==["runtime","extensions","risk"]
            ):
                try:
                    actor=self._actor()
                    q=parse_qs(urlsplit(self.path).query,strict_parsing=True)
                    if set(q)!={"supplier_score","months_active"} or any(
                        len(values)!=1 or not re.fullmatch(r"[0-9]{1,3}",values[0])
                        for values in q.values()
                    ):
                        raise Rejected(422,"RISK_CONTEXT_INVALID")
                    result=registry.score_record(
                        actor,parts[2],parts[6],int(q["supplier_score"][0]),
                        int(q["months_active"][0]))
                    self._json(200,result)
                except Rejected as e:
                    self._json(e.status,{"error":e.code})
                except (RuleError,ValueError):
                    self._json(422,{"error":"RISK_CONTEXT_INVALID"})
                except Exception:
                    self._json(503,{"error":"EXTENSION_UNAVAILABLE"})
                return
            return super().do_GET()
    return ThreadingHTTPServer(("127.0.0.1",0),Handler)
