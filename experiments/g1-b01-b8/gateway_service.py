"""B8 trusted gateway process over a REAL Saltcorn SQLite database.

Uses the existing independently previously tested Saltcorn governed gateway,
unchanged. Only mode-0700 Saltcorn DB owner may launch it.

The gateway is an extra research write entry, NOT a replacement of Saltcorn's
native /field route. B8 intentionally demonstrates that route still bypasses.
"""
from __future__ import annotations
import argparse,json,os,sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from gateway import Server


def serve(config,ready):
    cfg=Path(config)
    if cfg.stat().st_mode & 0o077:
        raise RuntimeError("B8_GATEWAY_CONFIG_MODE_UNSAFE")
    args=json.loads(cfg.read_text())
    if set(args)!={"db","humanPassword","agentToken","readToken"}:
        raise RuntimeError("B8_GATEWAY_CONFIG_SHAPE")
    db=Path(args["db"])
    if db.parent.stat().st_mode & 0o077 or not db.is_file():
        raise RuntimeError("B8_SALTCORN_DB_UNSAFE")
    server=Server(("127.0.0.1",0),str(db),args["humanPassword"],
                  args["agentToken"],args["readToken"],False)
    data={"scope":"B8_SALTCORN_NATIVE_NEGATIVE_CONTROL",
          "port":server.server_port,"pid":os.getpid(),"uid":os.getuid()}
    p=Path(ready)
    p.write_text(json.dumps(data),encoding="utf-8")
    p.chmod(0o644)
    print("S1_B8_GATEWAY_READY|"+json.dumps({"uid":os.getuid()}),flush=True)
    try:server.serve_forever(poll_interval=.15)
    finally:server.server_close()


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--config",required=True)
    p.add_argument("--ready",required=True)
    a=p.parse_args()
    serve(a.config,a.ready)
