# Gate-1 V06 Immutability Evidence

Status: `CONTRACT_FROZEN / GIT_RESOLVER_IMPLEMENTED / REAL_KERNEL_INTEGRATION_PENDING`

This directory defines the institution-neutral evidence boundary for Gate-1 V06.

```text
immutability/
├── README.md
├── binding-spec.md
├── immutability-contract.md
├── resolver-interface.md
├── git_commit_chain.py
└── schemas/
    ├── PUBLIC_REPLAY_IMMUTABILITY_BINDING_v0.1.schema.json
    ├── GIT_COMMIT_CHAIN_v0.1.schema.json
    ├── GIT_OBJECT_PROOF_v0.1.schema.json
    ├── GIT_NO_OVERWRITE_ATTESTATION_v0.1.schema.json
    ├── WORM_STORE_ATTESTATION_v0.1.schema.json
    └── IPFS_PIN_v0.1.schema.json
```

## Boundary

```text
V06 proves: captured corpus storage is sealed against in-place overwrite.
V06 does not prove: source truth, source permanence, policy correctness, availability forever, or authority.
```

## Cycle-free seal ordering

```text
manifest_bytes
-> H_manifest
-> immutability evidence
-> content-addressed immutability binding
-> offline Gate1
```

The manifest never contains a post-manifest `immutability_evidence_ref`. The binding defined by `binding-spec.md` selects the evidence after `H_manifest` exists.

## Prior contract-freeze evidence

The original generic surface-test gate passed at commit:

```text
HEAD_SHA=13701b359f2d66c0bcfa45de49e621026ade3df7
TEST_FILE_SHA256=14c6ddb10797c1e0977f5a04651ea7420d517d468ccdad675f004021fdc8caed
PYTHON=Python 3.12.3
TEST_EXIT=0
TEST_RESULT=PASS
RAW_LOG_SHA256=37d8a0769d6c800296764c21f8e08feca52d770d400afabe65713604062cf749
```

That receipt remains valid evidence for that exact historical head. It does not certify later verifier/resolver code.

## Current implementation state

```text
CONTRACT_FROZEN = TRUE
GIT_RESOLVER_IMPLEMENTED = TRUE
GIT_RESOLVER = GIT_COMMIT_CHAIN_RESOLVER_v0.1
REAL_RECEIPTOS_KERNEL_INTEGRATION_TEST = WRITTEN
REAL_RECEIPTOS_KERNEL_INTEGRATION_RECEIPT = MISSING
CLI_WIRED_TO_GIT_RESOLVER = FALSE
PRODUCTION_V06_PASS = PROHIBITED
PRODUCTION_GATE1_PASS = PROHIBITED
```

The production CLI deliberately continues to use `UNRESOLVED_IMMUTABILITY_FAIL_CLOSED_v0.1` until the rebuilt generic surface tests and the real-kernel Git integration tests execute independently on the exact new head.

No schema or implementation self-certifies its own sufficiency.
