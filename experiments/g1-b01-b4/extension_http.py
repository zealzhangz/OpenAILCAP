"""Research-only B4 read-only runtime REST integration using B2 sessions.

The client cannot submit Python or select a Docker image. Human/Agent code
writes and publication are NEVER exposed as HTTP runtime API routes.
"""
from __future__ import annotations

import re
from urllib.parse import parse_qs,urlsplit,unquote
from http.server import ThreadingHTTPServer

from schema_core import Rejected
from schema_http import handler_for


def server_with_extension(b2,registry,tokens,sessions,human,password):
    Parent=handler_for(b2,tokens,sessions,human,password)

    class RuntimeHandler(Parent):
        def do_GET(self):
            path=urlsplit(self.path)
            parts=[unquote(p) for p in path.path.split("/") if p]
            if (len(parts)==7 and parts[0]=="v2" and parts[1]=="apps" and
                parts[3:6]==["runtime","extensions","risk"]):
                try:
                    actor=self._actor()
                    q=parse_qs(path.query,keep_blank_values=True,strict_parsing=True)
                    if set(q)!={"supplier_score","months_active"} or (
                        any(len(values)!=1 or not re.fullmatch(r"[0-9]{1,3}",values[0])
                            for values in q.values())
                    ):
                        raise Rejected(422,"RISK_CONTEXT_INVALID")
                    result=registry.score_record(
                        actor,parts[2],parts[6],
                        int(q["supplier_score"][0]),int(q["months_active"][0]))
                    self._json(200,result)
                except (ValueError,Rejected) as e:
                    self._json(e.status if isinstance(e,Rejected) else 422,{
                        "error":e.code if isinstance(e,Rejected) else "RISK_CONTEXT_INVALID"})
                except Exception:
                    self._json(503,{"error":"EXTENSION_UNAVAILABLE"})
                return
            super().do_GET()
    return ThreadingHTTPServer(("127.0.0.1",0),RuntimeHandler)
