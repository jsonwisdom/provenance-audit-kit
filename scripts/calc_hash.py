#!/usr/bin/env python3
import argparse, hashlib, json, pathlib, sys

def canonical_hash(path: pathlib.Path) -> str:
    data = json.loads(path.read_text(encoding="utf-8"))

    if "hash" not in data:
        raise SystemExit(f"ERROR: missing hash field: {path}")

    original = data.get("hash")
    data["hash"] = ""

    canonical = json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")

    digest = hashlib.sha256(canonical).hexdigest()

    print(f"path: {path}")
    print(f"current_hash: {original}")
    print(f"canonical_hash: {digest}")
    return digest

def write_hash(path: pathlib.Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    data["hash"] = ""

    canonical = json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")

    data["hash"] = hashlib.sha256(canonical).hexdigest()

    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"WROTE {path}")
    print(f"hash: {data['hash']}")

def main():
    p = argparse.ArgumentParser()
    p.add_argument("file")
    p.add_argument("--write", action="store_true")
    args = p.parse_args()

    path = pathlib.Path(args.file)

    if args.write:
        write_hash(path)
    else:
        canonical_hash(path)

if __name__ == "__main__":
    main()
