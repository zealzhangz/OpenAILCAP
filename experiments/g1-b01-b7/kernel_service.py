"""S1 B7: separate unprivileged Linux uid owns authoritative SQLite.

The service is run with runuser(1) by a *trusted* test controller, not by
Agent, plugin or CLI. It is the only non-root identity permitted to traverse
the private directory and access B2/B4 SQLite. Other uids call scoped B5
v3 typed tools on loopback; browser human uses B2 session+CSRF.

Not a complete microservice / network-auth architecture: loopback remains
reachable to any local uid WITH a grant, root remains omnipotent.
"""
from __future__ import annotations

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


class NoBuildAccess:
    """B7 never provides a Docker socket to the DB-owning kernel process."""
    def test(self,*_):
        raise RuntimeError("BUILD_EXECUTION_NOT_GRANTED_TO_KERNEL")


def load_config(filename):
    p=Path(filename)
    if p.stat().st_mode & 0o077:
        raise RuntimeError("KERNEL_CONFIG_NOT_PRIVATE")
    data=json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data,dict) or set(data)!={
        "dbPath","password","agentToken","pluginToken","runtimeToken"
    }:
        raise RuntimeError("CONFIG_SHAPE_INVALID")
    if not all(isinstance(data[k],str) and len(data[k])>=24 for k in
               ("password","agentToken","pluginToken","runtimeToken")):
        raise RuntimeError("CREDENTIALS_NOT_SET")
    return data


def serve(config,ready):
    os.umask(0o077)
    cfg=load_config(config)
    dbpath=Path(cfg["dbPath"])
    if dbpath.parent.stat().st_mode & 0o077:
        raise RuntimeError("DB_DIRECTORY_NOT_PRIVATE")
    store=SchemaStore(dbpath)
    store.init()
    for app in ("app-a","app-b"):
        store.seed_app_for_test(app)
    dbpath.chmod(0o600)
    registry=ExtensionRegistry(store,NoBuildAccess())
    registry.init()
    broker=ToolBroker(store,registry)
    actor_human=Actor("b7-human-reviewer","app-a",can_publish=True,can_runtime=True)
    actor_agent=Actor("b7-agent","app-a")
    actor_plugin=Actor("b7-native-plugin","app-a",kinds=("view",))
    actor_runtime=Actor("b7-runtime","app-a",can_runtime=True)
    broker.grant(cfg["agentToken"],actor_agent,{"draft.read","metadata.upsert"})
    broker.grant(cfg["pluginToken"],actor_plugin,{"draft.read","metadata.upsert"})
    broker.grant(cfg["runtimeToken"],actor_runtime,{
        "release.read","form.submit","workflow.advance"})
    sessions={}
    server=make_server(store,registry,broker,sessions,actor_human,cfg["password"])
    if server.server_address[0]!="127.0.0.1":
        raise RuntimeError("NON_LOOPBACK_BIND_FORBIDDEN")
    # Ready-file contains NO credentials. Parent directory writable by the
    # kernel only; trusted orchestrator can read the public port and verify.
    readyfile=Path(ready)
    readyfile.write_text(json.dumps({
        "port":server.server_port,"kernelUid":os.getuid(),
        "kernelPid":os.getpid(),"scope":"S1_B7_OS_DAC_EXPERIMENT"
    }),encoding="utf-8")
    readyfile.chmod(0o644)
    print("S1_B7_KERNEL_LISTENING|uid="+str(os.getuid()),flush=True)
    try:server.serve_forever(poll_interval=0.1)
    finally:server.server_close()


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--config",required=True)
    p.add_argument("--ready",required=True)
    args=p.parse_args()
    serve(args.config,args.ready)
