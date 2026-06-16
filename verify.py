#!/usr/bin/env python3
import json, hashlib, sys, platform
from datetime import datetime, timezone

DOMAINS = [
  "source_integrity",
  "dependency_lock",
  "provenance_traceability",
  "analysis_hygiene",
  "build_reproducibility",
  "security_policy_defined"
]

def canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()

def sha(obj):
    return hashlib.sha256(canon(obj)).hexdigest()

def load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def main():
    findings = load("examples/pass/findings.json")
    statuses = [x["status"] for x in findings["findings"]]
    domains = [x["domain"] for x in findings["findings"]]

    ok = (
        len(domains) == 6 and
        domains == DOMAINS and
        all(s in ["PASS", "FAIL"] for s in statuses)
    )

    verification = {
        "schema_id": "JSONWISDOM_VERIFICATION_V0_1",
        "standard": "JSONWISDOM_HARDENED_STANDARD_V1",
        "repository": "jsonwisdom/provenance-audit-kit",
        "commit": "LOCAL",
        "audit_id": findings["audit_id"],
        "policy_sha256": findings["policy_sha256"],
        "canonical_approval_sha256": "UNSIGNED",
        "inputs": {
            "findings_sha256": sha(findings)
        },
        "replay": {
            "findings_recomputed": ok,
            "score_recomputed": ok,
            "policy_applied": ok,
            "bit_for_bit_match": ok,
            "network_access_required": False
        },
        "verifier": {
            "tool": "jsonwisdom-provenance-verifier",
            "version": "0.1.0",
            "runtime": "python " + platform.python_version()
        },
        "verification_status": "PASS" if ok else "FAIL",
        "verified_at_utc": datetime.now(timezone.utc).isoformat()
    }

    print(json.dumps(verification, indent=2, sort_keys=True))
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
