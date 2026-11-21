"""B15 narrowly scoped Linux netfilter native-HTTP bypass denial.

Only the trusted Router UID may connect to the Native Saltcorn TCP port via
loopback. Other local UIDs (including the CI runner/Chromium) are rejected
by OUTPUT owner match. Non-loopback ingress is rejected by INPUT.
IPv4 AND IPv6 rules, with exact-match idempotent cleanup.
Root/CAP_NET_ADMIN can override; not a container/production network policy.
"""
from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys

COMMENT="OpenAILCAP-B15-NATIVE-ONLY-TRUSTED-ROUTER"


def rules(port,router_uid):
    def common():
        return ["-p","tcp","--dport",str(port),"-m","comment",
                "--comment",COMMENT]
    return [
        ("iptables","OUTPUT",common()+["-d","127.0.0.1",
            "-m","owner","!","--uid-owner",str(router_uid),"-j","REJECT"]),
        ("iptables","INPUT",common()+["!","-i","lo","-j","REJECT"]),
        ("ip6tables","OUTPUT",common()+["-d","::1",
            "-m","owner","!","--uid-owner",str(router_uid),"-j","REJECT"]),
        ("ip6tables","INPUT",common()+["!","-i","lo","-j","REJECT"])
    ]


def cmd(binary,verb,chain,parts):
    return subprocess.run([binary,"-w",verb,chain,*parts],
                          text=True,capture_output=True,timeout=10)


def apply(action,port,uid):
    if os.geteuid()!=0:
        raise RuntimeError("NETFILTER_ROOT_REQUIRED")
    if not (1024<=port<=65535 and uid>0):
        raise RuntimeError("NETFILTER_SCOPE_INVALID")
    rs=rules(port,uid)
    if action=="enable":
        changed=[]
        try:
            for binary,chain,parts in rs:
                if cmd(binary,"-C",chain,parts).returncode==0:continue
                result=cmd(binary,"-I",chain,["1",*parts])
                if result.returncode:
                    raise RuntimeError("NETFILTER_INSERT_FAILED "+
                                       binary+" "+result.stderr[-400:])
                changed.append((binary,chain,parts))
        except Exception:
            for binary,chain,parts in reversed(changed):
                cmd(binary,"-D",chain,parts)
            raise
    elif action=="disable":
        for binary,chain,parts in reversed(rs):
            if cmd(binary,"-C",chain,parts).returncode==0:
                result=cmd(binary,"-D",chain,parts)
                if result.returncode:
                    raise RuntimeError("NETFILTER_REMOVE_FAILED "+binary)
    elif action!="status":
        raise RuntimeError("NETFILTER_ACTION_INVALID")
    state=[cmd(binary,"-C",chain,parts).returncode==0
           for binary,chain,parts in rs]
    return {"action":action,"installed":state,
            "allInstalled":all(state),"allAbsent":not any(state),
            "routerUid":uid,"nativePort":port,
            "ipv4AndIpv6":True}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("action",choices=("enable","disable","status"))
    p.add_argument("--native-port",type=int,required=True)
    p.add_argument("--router-uid",type=int,required=True)
    args=p.parse_args()
    print("S1_B15_FIREWALL|"+json.dumps(
        apply(args.action,args.native_port,args.router_uid)),flush=True)


if __name__=="__main__":
    main()
