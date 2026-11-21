"""Save installed upstream source hashes and line anchors with runtime evidence."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

root = Path(subprocess.check_output(["npm", "root", "-g"], text=True).strip())
cli = root / "@saltcorn/cli"
output = Path(sys.argv[1])
output.mkdir(parents=True, exist_ok=True)
manifest = []
for package, relative, anchors in (
    ("cli", "src/commands/serve.js", ["nomigrate", "noscheduler"]),
    ("server", "dist/serve.js", ["initOfflineStoreCfg", "pre_installed_module_infos", "initMaster"]),
    ("server", "dist/routes/utils.js", ["getSessionStore", "getExpressSessionStore"]),
    ("sqlite", "dist/sqlite.js", ["new sqlite3.Database", "get_session_filepath", "getExpressSessionStore"]),
):
    folder = cli if package == "cli" else cli / "node_modules/@saltcorn" / package
    source = folder / relative
    content = source.read_bytes()
    version = json.loads((folder / "package.json").read_text())["version"]
    filename = package + "-" + relative.replace("/", "-")
    (output / filename).write_bytes(content)
    manifest.append({"package": "@saltcorn/" + package, "version": version,
                     "path": relative, "sha256": hashlib.sha256(content).hexdigest(),
                     "anchors": [{"line": i, "text": line.strip()} for i, line in
                                 enumerate(content.decode().splitlines(), 1)
                                 if any(anchor in line for anchor in anchors)]})
(output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(json.dumps(manifest))
