#!/usr/bin/env python3
"""Read-only compiled Saltcorn native routes inspection. No secrets, no patch."""
from pathlib import Path
import os
import subprocess

root=Path(subprocess.check_output(["npm","root","-g"],text=True).strip())
print("npm_root:",root)
candidates=list(root.glob("**/routes/fields.js"))
print("matches:",len(candidates))
for p in candidates[:20]:
    t=p.read_text(errors="replace")
    if "fieldFlow" not in t and "Field" not in t:
        continue
    print("PATH",p,"BYTES",len(t))
    print("HEADER",repr(t[:1100]))
    for pattern in ["fieldFlow =", "fieldFlow(", "fieldFlow = (", "await field.update(fldRow)", "field.update(fldRow)", "...field.toJson", "field.toJson", "Field.findOne({ id: context.id", '"/:id"', '"field"']:
        ix=t.find(pattern)
        print("ANCHOR",repr(pattern),"POS",ix)
        if ix>=0:
            print("EXCERPT",t[max(0,ix-350):min(len(t),ix+1100)])
    print("END_OF_FILE_MATCH")
