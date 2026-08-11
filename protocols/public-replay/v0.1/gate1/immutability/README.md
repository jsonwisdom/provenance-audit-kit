# Gate-1 V06 Immutability Evidence

Status: `FROZEN / INDEPENDENT_SURFACE_TEST_PASSED`

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

## Contract freeze evidence

The independent surface-test gate has passed and the raw test output is retained under:

```text
gate1/test-receipts/13701b359f2d66c0bcfa45de49e621026ade3df7/
```

Bound receipt facts:

```text
HEAD_SHA=13701b359f2d66c0bcfa45de49e621026ade3df7
TEST_FILE_SHA256=14c6ddb10797c1e0977f5a04651ea7420d517d468ccdad675f004021fdc8caed
PYTHON=Python 3.12.3
TEST_EXIT=0
TEST_RESULT=PASS
RAW_LOG_SHA256=37d8a0769d6c800296764c21f8e08feca52d770d400afabe65713604062cf749
```

## Current production state

```text
CONTRACT_FROZEN = TRUE
PRODUCTION_RESOLVER = UNRESOLVED_IMMUTABILITY_FAIL_CLOSED_v0.1
PRODUCTION_RESOLVER_IMPLEMENTED = FALSE
PRODUCTION_V06_PASS = IMPOSSIBLE
PRODUCTION_GATE1_PASS = IMPOSSIBLE
```

The contract may now be used as the specification for a later production resolver implementation, but that is a separate explicit transition. This freeze does not itself create `V06=PASS` or `H_G1^PASS`.

No schema in this directory self-certifies its own sufficiency.
