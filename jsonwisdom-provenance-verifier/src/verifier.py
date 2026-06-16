#!/usr/bin/env python3
import json, sys, os
from pathlib import Path
from enum import Enum

class State(Enum):
    INIT="INIT"; LOAD_ARTIFACTS="LOAD_ARTIFACTS"; SCHEMA_VALIDATION="SCHEMA_VALIDATION"; REPLAY_COMPUTE="REPLAY_COMPUTE"; VERDICT_COMPARISON="VERDICT_COMPARISON"; HALT="HALT"

class VerifierMachine:
    def __init__(self, workdir):
        self.workdir = Path(workdir)
        self.state = State.INIT
        self.artifacts = {}
        self.computed = {}
        self.verification = {"verifier":"jsonwisdom-provenance-verifier v0.1.0","verification_status":None,"bit_for_bit_match":False,"network_access_required":False,"fatal_error":None}

    def canonical_json(self, obj):
        return json.dumps(obj, sort_keys=True, separators=(',', ':'))

    def fatal(self, msg):
        self.verification["verification_status"] = "FAIL"
        self.verification["fatal_error"] = msg
        self.halt()
        sys.exit(1)

    def halt(self):
        (self.workdir / "verification.json").write_text(self.canonical_json(self.verification) + "\n")
        self.state = State.HALT

    def run(self):
        if not self.workdir.is_dir(): self.fatal("INIT: workdir not local directory")
        if os.environ.get("ALLOW_NETWORK") == "1": self.fatal("INIT: Network airgap violated")

        for f in ["policy.json","evidence.json","findings.json","score.json"]:
            p = self.workdir / f
            if not p.exists(): self.fatal(f"LOAD_ARTIFACTS: Missing {f}")
            self.artifacts[f] = json.loads(p.read_text())
            if not isinstance(self.artifacts[f], dict): self.fatal(f"SCHEMA_VALIDATION: {f} not object")

        policy = self.artifacts["policy.json"]
        evidence = self.artifacts["evidence.json"]
        findings = {"checks":[]}
        score = {"max":0,"total":0}

        for rule in policy.get("rules", []):
            passed = rule["id"] in evidence.get("passed_rules", [])
            findings["checks"].append({"pass": passed, "rule": rule["id"]})
            weight = rule.get("weight", 1)
            score["max"] += weight
            if passed: score["total"] += weight

        self.computed["findings.json"] = findings
        self.computed["score.json"] = score

        for f in ["findings.json","score.json"]:
            if self.canonical_json(self.artifacts[f]) != self.canonical_json(self.computed[f]):
                self.fatal(f"VERDICT_COMPARISON: Mismatch in {f}")

        self.verification["verification_status"] = "PASS"
        self.verification["bit_for_bit_match"] = True
        self.halt()
        return 0

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: verifier.py <workdir>", file=sys.stderr)
        sys.exit(2)
    sys.exit(VerifierMachine(sys.argv[1]).run())
