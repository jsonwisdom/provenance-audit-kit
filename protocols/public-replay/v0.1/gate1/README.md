# PUBLIC_REPLAY_GATE1_v0.1

Status: IMPLEMENTED / FAIL-CLOSED / GIT V06 INTEGRATION PASSED / CLI UNWIRED

This directory implements the institution-neutral offline Gate-1 boundary for `PUBLIC_REPLAY_PROTOCOL_v0.1`.

```text
manifest.jsonl
+ corpus/raw/
+ profile.json
+ immutability/bindings/<H_binding>.json
+ referenced immutability evidence/proofs
                |
                v
       PUBLIC_REPLAY_GATE1_v0.1
                |
                v
        profile receipt + H_G1
```

## Hard boundaries

```text
GATE1 != ACQUISITION
GATE1 != SEALING PHASE
GATE1 != INSTITUTION
GATE1 != KNOWLEDGE STATE
GATE1 != WITNESS
```

The verifier performs no network acquisition, refetch, repair, source-byte normalization, or policy interpretation.

`network_used=false` is hard-coded. `network_guard.py` blocks socket creation/name resolution/connection and child-process/system-spawn attempts at runtime.

## Cycle-free V06 input

The manifest contains no post-manifest immutability reference.

```text
manifest_bytes
-> H_manifest
-> immutability evidence
-> H_binding
-> Gate1
```

The verifier recomputes both `H_manifest` and `H_binding`. A binding selects exactly one content-addressed evidence object in v0.1.

## ReceiptOS kernel dependency

The verifier loads exact local ReceiptOS rails:

```text
ep/canonical.py::canonicalize
receiptos/core/hash.py::canonical_json
```

Their exact source SHA-256 values are bound into the Gate-1 receipt.

Missing kernel files/imports fail closed. The verifier never silently substitutes an internal serializer.

## Verifier and resolver identity

The canonical receipt also binds:

```text
verifier_sha256
immutability_resolver.resolver_id
immutability_resolver.implementation_sha256
```

So “same verifier/resolver” is a content identity, not a label.

## Determinism

```text
canonical_receipt_bytes = UTF8(receiptos.core.hash.canonical_json(receipt)) + LF
H_G1 = SHA256(canonical_receipt_bytes)
H_G1 NOT_IN canonical_receipt_bytes
```

No wall-clock `verified_at` is included in canonical receipt bytes.

## V01-V08

```text
V01 canonical manifest form + row structure
V02 raw-object existence
V03 raw-object SHA-256/content-address binding
V04 exact byte lengths
V05 capture/scope/profile binding + admitted-row constraints
V06 cycle-free binding + verified sufficient storage-seal evidence
V07 declared-scope completion from manifest/profile
V08 promotion predicate over V01-V07 + zero integrity counters
```

A required acquisition failure leaves the required admitted row absent, so V07 fails without inspecting hidden sibling failure directories.

## V06 implementation posture

The generic `GIT_COMMIT_CHAIN_RESOLVER_v0.1` is implemented under:

```text
gate1/immutability/git_commit_chain.py
```

It verifies Git commit/tree/blob identities from exact offline proof bytes without invoking `git`, ignores branch names, binds the exact current manifest/raw set, and can verify a prior-manifest parent chain.

An independent Google Cloud Shell execution at Gate-1 head:

```text
76272ebe789c86a85a7af512019c139ea72c70b5
```

passed both suites:

```text
surface tests: 8 / PASS
real ReceiptOS kernel + Git V06 integration tests: 3 / PASS
raw integration log SHA-256: 67b9862251c870631f63a566ff263d71be371ec09c653c381d2f6c30a393225a
```

The ReceiptOS checkout reported a dirty worktree, but the two kernel files actually loaded by Gate 1 matched the committed ReceiptOS head `7cc484e2803327170c3b96543f2735a1f95655b4` byte-for-byte by SHA-256:

```text
ep/canonical.py = 1c20180d08b0944e6328eca48d3edee46d43ca11aae634d35607c5629dad2cbe
receiptos/core/hash.py = 79a1206ebbbf93e6b76ce060e4b3d12ac0f84161253361dcc8388e2070c8c4c3
```

Retained execution evidence lives under:

```text
gate1/test-receipts/76272ebe789c86a85a7af512019c139ea72c70b5/
```

Current posture:

```text
GIT_RESOLVER_IMPLEMENTED = TRUE
REAL_KERNEL_INTEGRATION_TEST_WRITTEN = TRUE
REAL_KERNEL_INTEGRATION_RECEIPT = PASS
CLI_RESOLVER = UNRESOLVED_IMMUTABILITY_FAIL_CLOSED_v0.1
PRODUCTION_V06_PASS = PROHIBITED
PRODUCTION_GATE1_PASS = PROHIBITED
```

The integration receipt clears the resolver implementation test gate only. The production CLI remains deliberately unwired until a separate explicit promotion transition changes that boundary.

## Profile

The profile is data, not executable verifier code. It binds:

```text
protocol_id
profile_id
scope_id
corpus_id
receipt_schema
required_urls[]
allowed_urls[]
success_status_codes[]
```

A profile is itself ReceiptOS byte-strict canonical JSON + LF and its exact bytes are hashed as `profile_sha256`.

SSA is one profile. White House or later institutions use the same generic verifier with a different profile/scope.
