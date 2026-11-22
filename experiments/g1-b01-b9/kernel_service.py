"""B9 trusted B2/B4/B5 Domain Kernel with publisher capability.

Authoritative DB/config stored under a private OS owner, never copied into
Saltcorn. Trusted test coordinator owns two per-app publisher grants; native
Saltcorn runtime process gets no broker token or authority DB access.

WARNING: trusted coordinator still sudo-capable in this research CI fixture;
publisher is a simulated human permission, not real enterprise SSO.
"""
import argparse
import json
import os
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"g1-b01-b2"))
sys.path.insert(0,str(HERE.parent/"g1-b01-b4"))
sys.path.insert(0,str(HERE.parent/"g1-b01-b5"))
sys.path.insert(0,str(HERE.parent/"g1-b01-b11"))
from schema_core import Actor,SchemaStore,Rejected
from registry import ExtensionRegistry
from tool_broker import ToolBroker,make_server
from projection_source import install as install_b11_outbox
from p0b_authority_business import read_business,AuthorityDataRejected
from p0b_activation import Activation,ActivationRejected,initialize as initialize_activation


class BusinessHeadKernelBroker(ToolBroker):
    """B9-only scoped read under the EXISTING runtimeToken release.read grant.

    The public tool name business.head is intercepted here and never added
    to B5's global capability list. Agent and Plugin lack release.read.
    """
    def __init__(self,store,registry):
        super().__init__(store,registry)
        self.activation=Activation(store.path)

    def call(self,token,app,tool,args):
        if tool in ("publication.read","publication.activate"):
            if tool=="publication.read":
                self.authorize(token,app,"release.read")
                self._shape(args,())
                if app!="app-a":
                    raise Rejected(403,"ACTIVATION_APP_FORBIDDEN")
                try:return self.activation.read()
                except ActivationRejected as err:
                    raise Rejected(err.status,err.code) from None
            actor=self.authorize(token,app,"app.publish")
            SchemaStore.authorize(actor,app,publish=True)
            if app!="app-a":
                raise Rejected(403,"ACTIVATION_APP_FORBIDDEN")
            try:
                return self.activation.activate(actor.name,args)
            except ActivationRejected as err:
                raise Rejected(err.status,err.code) from None
        if tool!="business.head":
            return super().call(token,app,tool,args)
        self.authorize(token,app,"release.read")
        self._shape(args,())
        if app!="app-a":
            raise Rejected(403,"BUSINESS_HEAD_APP_FORBIDDEN")
        try:
            head=read_business(self.store.path)
        except AuthorityDataRejected as e:
            raise Rejected(503,e.code) from None
        return {"app":"app-a","head":head["head"],
                "rowsDigest":head["rowsDigest"]}


class NoBuildInKernel:
    def test(self,*_):
        raise RuntimeError("KERNEL_DOCKER_BUILD_DISABLED")


def serve(config_path,ready_path):
    os.umask(0o077)
    p=Path(config_path)
    if p.stat().st_mode & 0o077:
        raise RuntimeError("KERNEL_CONFIG_NOT_PRIVATE")
    cfg=json.loads(p.read_text(encoding="utf-8"))
    required={"dbPath","humanPassword","agentToken","publisherToken",
              "runtimeToken","appBPublisherToken","pluginToken"}
    if not isinstance(cfg,dict) or set(cfg)!=required or any(
            not isinstance(cfg[k],str) or len(cfg[k])<24
            for k in required-{"dbPath"}):
        raise RuntimeError("KERNEL_CONFIG_INVALID")
    dbfile=Path(cfg["dbPath"])
    if dbfile.parent.stat().st_mode & 0o077:
        raise RuntimeError("KERNEL_DB_DIR_NOT_PRIVATE")
    store=SchemaStore(dbfile)
    store.init()
    for app in ("app-a","app-b"):
        store.seed_app_for_test(app)
    # B11 real AFTER-record-write triggers in the SAME authority.sqlite, not
    # an independently populated demonstration database.
    install_b11_outbox(dbfile)
    initialize_activation(dbfile)
    dbfile.chmod(0o600)
    registry=ExtensionRegistry(store,NoBuildInKernel())
    registry.init()
    broker=BusinessHeadKernelBroker(store,registry)
    human=Actor("b9-human-web","app-a",can_publish=True,can_runtime=True)
    agent=Actor("b9-agent","app-a")
    plugin=Actor("p0a-native-plugin","app-a",kinds=("view",))
    publisher=Actor("b9-human-approved-release","app-a",can_publish=True)
    runtime=Actor("b9-release-export-reader","app-a",can_runtime=True)
    bp=Actor("b9-app-b-human-approved","app-b",can_publish=True)
    broker.grant(cfg["agentToken"],agent,
                 {"draft.read","metadata.upsert"})
    broker.grant(cfg["pluginToken"],plugin,
                 {"draft.read","metadata.upsert"})
    broker.grant(cfg["publisherToken"],publisher,
                 {"draft.read","app.publish","app.rollback","release.read"})
    broker.grant(cfg["runtimeToken"],runtime,{"release.read"})
    broker.grant(cfg["appBPublisherToken"],bp,{"release.read"})
    server=make_server(store,registry,broker,{},human,cfg["humanPassword"])
    if server.server_address[0]!="127.0.0.1":
        raise RuntimeError("KERNEL_NOT_LOOPBACK")
    Path(ready_path).write_text(json.dumps({
        "port":server.server_port,
        "pid":os.getpid(),
        "uid":os.getuid(),
        "scope":"S1_B9_AUTHORITATIVE_ONLY"
    }),encoding="utf-8")
    Path(ready_path).chmod(0o644)
    print("S1_B9_KERNEL_READY|"+json.dumps({"uid":os.getuid()}),flush=True)
    try:server.serve_forever(poll_interval=.1)
    finally:server.server_close()


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--config",required=True)
    parser.add_argument("--ready",required=True)
    args=parser.parse_args()
    serve(args.config,args.ready)
