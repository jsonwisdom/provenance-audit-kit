# Gate-1 V06 Immutability Evidence

Status: `FROZEN_DRAFT / TEST_EXECUTION_PENDING`

This directory defines the institution-neutral evidence contract required before production Gate-1 may ever assign `V06=PASS`.

```text
immutability/
├── README.md
├── immutability-contract.md
├── resolver-interface.md
└── schemas/
    ├── GIT_COMMIT_CHAIN_v0.1.schema.json
    ├── WORM_STORE_ATTESTATION_v0.1.schema.json
    └── IPFS_PIN_v0.1.schema.json
```

## Boundary

```text
V06 proves: captured corpus storage is sealed against in-place overwrite.
V06 does not prove: source truth, source permanence, policy correctness, availability forever, or authority.
```

## Current production state

```text
PRODUCTION_RESOLVER = UNRESOLVED_IMMUTABILITY_FAIL_CLOSED_v0.1
PRODUCTION_V06_PASS = IMPOSSIBLE
PRODUCTION_GATE1_PASS = IMPOSSIBLE
```

A production resolver implementation is prohibited until:

1. `gate1/tests/test_gate1_surface.py` is executed in an independent local environment;
2. raw execution output is retained;
3. this contract is reviewed against that execution evidence;
4. the contract status is explicitly promoted beyond `TEST_EXECUTION_PENDING`.

No schema in this directory self-certifies its own sufficiency.
