#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
from pathlib import Path

ENGINE = Path(__file__).parent / "jsonwisdom-provenance-verifier" / "src" / "verifier.py"


def main():
    parser = argparse.ArgumentParser(description="Thin frontend for jsonwisdom-provenance-verifier")
    parser.add_argument("--path", required=True, help="Local verifier workdir")
    args = parser.parse_args()

    workdir = Path(args.path)
    if not workdir.is_dir():
        print(f"verify: workdir not found: {workdir}", file=sys.stderr)
        return 2
    if not ENGINE.is_file():
        print(f"verify: engine not found: {ENGINE}", file=sys.stderr)
        return 2

    result = subprocess.run([sys.executable, str(ENGINE), str(workdir)])

    verification = workdir / "verification.json"
    if verification.is_file():
        try:
            print(json.dumps(json.loads(verification.read_text()), indent=2, sort_keys=True))
        except (json.JSONDecodeError, OSError):
            print(verification.read_text(), end="")

    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
