"""One bounded, hash-pinned research change in an ephemeral CI installation.

NOT an upstream-supported read-only mode. Restore refuses unexpected content.
"""
import argparse
import hashlib
import json
from pathlib import Path

ORIGINAL_SHA = "8cac7fb41f671d831e3086ee2b481c92368350bd736bca9faae00fa0a626b0e0"
ANCHOR = "    await initOfflineStoreCfg();"
REPLACEMENT = "    console.log('B17_RESEARCH_SKIP_OFFLINE_STORE_CONFIG');"


def patched(original):
    if hashlib.sha256(original).hexdigest() != ORIGINAL_SHA:
        raise ValueError("UPSTREAM_SOURCE_DRIFT")
    if original.count(ANCHOR.encode()) != 1:
        raise ValueError("UPSTREAM_ANCHOR_DRIFT")
    return original.replace(ANCHOR.encode(), REPLACEMENT.encode())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("apply", "restore"))
    parser.add_argument("--file", type=Path, required=True)
    parser.add_argument("--backup", type=Path, required=True)
    args = parser.parse_args()
    if args.action == "apply":
        original = args.file.read_bytes()
        replacement = patched(original)
        with args.backup.open("xb") as stream:
            stream.write(original)
        args.file.write_bytes(replacement)
    else:
        original = args.backup.read_bytes()
        if args.file.read_bytes() != patched(original):
            raise ValueError("RESTORE_CONTENT_DRIFT")
        args.file.write_bytes(original)
    print(json.dumps({"action": args.action, "changedFiles": 1, "changedCalls": 1,
                      "sha256": hashlib.sha256(args.file.read_bytes()).hexdigest()}))


if __name__ == "__main__":
    main()
