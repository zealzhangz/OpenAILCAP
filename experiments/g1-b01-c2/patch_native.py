#!/usr/bin/env python3
"""Disposable patch to published Saltcorn /field route for a falsifiable C2 study.

WARNING: This is an UNOFFICIAL COMPILED-PACKAGE INSTRUMENTATION ONLY.
It is not a supported extension point and does NOT provide atomic compare+write.
Do not use it in production.
"""
from pathlib import Path
import subprocess
import sys

HELPER = """
// S1_C2_INSTRUMENT_BEGIN: research only, non-atomic stale-wizard check.
const s1C2Sign = async (id, label, userId) => {
  const secret = process.env.S1_C2_GUARD_SECRET;
  if (!secret || secret.length < 32) throw new Error("S1_C2_SECRET_MISSING");
  const { createHmac } = await import("node:crypto");
  return createHmac("sha256", secret)
    .update(JSON.stringify([String(id), String(label), String(userId)]))
    .digest("hex");
};
const s1C2Verify = async (context, field, userId) => {
  const base = context.__s1_c2_base_label;
  const signature = context.__s1_c2_signature;
  if (typeof base !== "string" || typeof signature !== "string")
    throw new Error("S1_C2_BASE_MISSING");
  const { timingSafeEqual } = await import("node:crypto");
  const correct = await s1C2Sign(field.id, base, userId);
  if (!/^[0-9a-f]{64}$/.test(signature) ||
      !timingSafeEqual(Buffer.from(signature, "hex"), Buffer.from(correct, "hex")))
    throw new Error("S1_C2_BASE_TAMPERED");
  if (String(field.label) !== base) throw new Error("S1_C2_STALE_EDITOR");
};
// S1_C2_INSTRUMENT_END.
"""
def one_replace(s, before, after):
    n=s.count(before)
    if n!=1:
        raise RuntimeError(f"Expected one native route anchor; saw {n}: {before[:100]}")
    return s.replace(before,after,1)

def main():
    root=Path(subprocess.check_output(["npm","root","-g"],text=True).strip())
    files=list(root.glob("**/routes/fields.js"))
    matches=[]
    for p in files:
        t=p.read_text(errors="replace")
        if "const fieldFlow =" in t and "await field.update(fldRow);" in t and "...field.toJson," in t:
            matches.append((p,t))
    if len(matches)!=1: raise RuntimeError(f"Expected one target native compiled field route: {len(matches)}")
    path,s=matches[0]
    if "S1_C2_INSTRUMENT" in s:
        raise RuntimeError("Already patched")
    s=one_replace(s,"const fieldFlow =",HELPER+"\nconst fieldFlow =")
    s=one_replace(
      s,"        ...field.toJson,\n",
      "        ...field.toJson,\n"
      "        __s1_c2_base_label: String(field.label),\n"
      "        __s1_c2_signature: await s1C2Sign(field.id, field.label, req.user?.id),\n"
    )
    s=one_replace(
      s,"                    await field.update(fldRow);",
      "                    await s1C2Verify(context, field, req.user?.id);\n"
      "                    await field.update(fldRow);",
    )
    s=one_replace(
      s,"    const wfres = await wf.run(req.body || {}, req);",
      "    const wfres = await wf.run(req.body || {}, req);\n"
      "    if (wfres.flash && [\"S1_C2_STALE_EDITOR\", \"S1_C2_BASE_MISSING\","
      " \"S1_C2_BASE_TAMPERED\"].includes(wfres.flash[1])) {\n"
      "      return res.status(409).json({error: wfres.flash[1], kind: \"S1_C2_UNOFFICIAL_ROUTE_PATCH\"});\n"
      "    }",
    )
    path.write_text(s)
    subprocess.run(["node","--check",str(path)],check=True)
    print("S1_C2_PATCH_APPLIED",{"path_basename":path.name,"native_route_instrumented":True,
        "installed_code_mutated_for_ephemeral_test_only":True,
        "atomic_cas":False,"direct_Field_update_bypass_still_possible":True})

if __name__=="__main__":
    main()
