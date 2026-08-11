# PUBLIC_REPLAY_GATE1_v0.1

Status: IMPLEMENTED / FAIL-CLOSED / GIT V06 INTEGRATION PENDING

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

However the production CLI is deliberately NOT wired to it yet.

```text
GIT_RESOLVER_IMPLEMENTED = TRUE
REAL_KERNEL_INTEGRATION_TEST_WRITTEN = TRUE
REAL_KERNEL_INTEGRATION_RECEIPT = MISSING
CLI_RESOLVER = UNRESOLVED_IMMUTABILITY_FAIL_CLOSED_v0.1
PRODUCTION_V06_PASS = PROHIBITED
PRODUCTION_GATE1_PASS = PROHIBITED
```

A new independent receipt must cover both the rebuilt generic surface suite and the real ReceiptOS kernel integration suite on the exact new head before the CLI may switch resolvers.

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
