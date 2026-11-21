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
from schema_core import Actor,SchemaStore
from registry import ExtensionRegistry
from tool_broker import ToolBroker,make_server


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
              "runtimeToken","appBPublisherToken"}
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
    dbfile.chmod(0o600)
    registry=ExtensionRegistry(store,NoBuildInKernel())
    registry.init()
    broker=ToolBroker(store,registry)
    human=Actor("b9-human-web","app-a",can_publish=True,can_runtime=True)
    agent=Actor("b9-agent","app-a")
    publisher=Actor("b9-human-approved-release","app-a",can_publish=True)
    runtime=Actor("b9-release-export-reader","app-a",can_runtime=True)
    bp=Actor("b9-app-b-human-approved","app-b",can_publish=True)
    broker.grant(cfg["agentToken"],agent,
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
