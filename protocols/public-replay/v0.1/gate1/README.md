# PUBLIC_REPLAY_GATE1_v0.1

Status: IMPLEMENTATION SURFACE / FAIL-CLOSED

This directory implements the institution-neutral offline Gate-1 boundary for `PUBLIC_REPLAY_PROTOCOL_v0.1`.

```text
manifest.jsonl + corpus/raw/ + profile.json
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
GATE1 != INSTITUTION
GATE1 != KNOWLEDGE STATE
GATE1 != WITNESS
```

The verifier performs no network acquisition, refetch, repair, normalization of source bytes, or policy interpretation.

`network_used = false` is hard-coded by the implementation. `network_guard.py` disables socket creation/name resolution/connection at import time and records any attempted network use as a fail-closed execution violation.

## ReceiptOS kernel dependency

The production CLI loads two existing ReceiptOS rails from a local `receiptos-base` checkout:

```text
ep/canonical.py::canonicalize
receiptos/core/hash.py::canonical_json
```

The first is used for byte-strict manifest/profile canonicalization. The second is used for deterministic Gate-1 receipt serialization.

The verifier records SHA-256 digests of both exact kernel source files in the receipt. Missing kernel files/imports fail closed. The verifier does not silently substitute an internal serializer.

## Determinism

Canonical receipt file bytes are:

```text
UTF8(receiptos.core.hash.canonical_json(receipt)) + LF
```

under serialization profile:

```text
RECEIPTOS_NFC_JSON_V1_LF
```

`H_G1` is external:

```text
H_G1 = SHA256(exact canonical receipt file bytes)
H_G1 NOT_IN receipt bytes
```

No wall-clock verification timestamp is included in the canonical Gate-1 receipt. Execution time belongs to external runner metadata so identical verification inputs can produce identical receipt bytes.

## V01-V08

```text
V01 canonical manifest form + row structure
V02 raw-object existence
V03 raw-object SHA-256/content-address binding
V04 exact byte lengths
V05 capture/scope/profile binding + admitted-row constraints
V06 verified sufficient historical immutability evidence
V07 declared-scope completion + zero acquisition-failure receipts
V08 promotion predicate over V01-V07 + zero integrity counters
```

`V08` creates no independent evidence. It is only the deterministic conjunction/promotion predicate.

## V06 posture

The generic surface defines an `ImmutabilityVerifier` interface. The CLI currently installs only the fail-closed resolver:

```text
UNRESOLVED_IMMUTABILITY -> V06 FAIL
```

A future immutability evidence verifier must be separately specified and reviewable before the CLI can produce `V06 = PASS`. Presence of a non-null reference never auto-passes V06.

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

The exact profile file bytes are hashed as `profile_sha256` and bound into the Gate-1 receipt.

SSA is one profile. White House or any later institution uses the same verifier with a different profile/scope input.
