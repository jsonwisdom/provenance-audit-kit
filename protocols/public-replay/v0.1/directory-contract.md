# PUBLIC_REPLAY_DIRECTORY_CONTRACT_v0.1

Status: FROZEN DRAFT  
Protocol: `PUBLIC_REPLAY_PROTOCOL_v0.1`

This contract defines where public-replay artifacts live and which classes may be mutated, derived, or omitted.

## 1. Layer separation

```text
PROTOCOL != INSTITUTION != CORPUS != KNOWLEDGE != WITNESS
```

The protocol defines reusable rules. Institution profiles specialize transport/scope metadata. Corpus instances contain observed evidence. Knowledge artifacts are derived only from verified corpus evidence. Witnesses bind already-created receipts and never create authority.

## 2. Canonical layout

```text
protocols/public-replay/v0.1/
  directory-contract.md
  profiles/
    <institution>/
      schemas/
  acquisition-spec.md            # future
  manifest-spec.md               # future
  gate1/                         # future pure verifier

audits/public-institutions/
  <institution>/
    <corpus_id>/
      scope/                      # INPUT
      acquisition/                # INPUT metadata/config; no verifier authority
      corpus/
        raw/                      # INPUT exact response bytes, content-addressed
        headers/                  # INPUT observed response headers
      manifests/                  # INPUT observation manifests
      receipts/
        fetch/                    # DERIVED from acquisition event
        failures/                 # DERIVED from failed acquisition event
        gate1/                    # DERIVED only by pure verifier
      knowledge/
        claims/                   # DERIVED; requires Gate-1 PASS
        policy-graph/             # DERIVED; requires Gate-1 PASS
        states/                   # DERIVED L3.6; requires Gate-1 PASS
        divergences/              # DERIVED
        contradiction-tests/      # DERIVED
        battles/                  # DERIVED
      witnesses/
        base/                     # OPTIONAL; requires H_G1^PASS
```

## 3. Artifact classes

### INPUT

Observed or operator-declared material that a later verifier consumes.

Examples:
- declared scope
- exact public response bytes `B_a`
- observed response headers
- `manifest.jsonl`

Rules:

```text
INPUT_CREATED -> IMMUTABLE
INPUT_CHANGED -> NEW_OBJECT_OR_NEW_CAPTURE
OVERWRITE -> PROHIBITED
```

Raw bytes are content-addressed:

```text
H_a = SHA256(B_a)
path(B_a) = corpus/raw/<H_a>
SHA256(read(path(B_a))) = <H_a>
```

A URL locates an observation. A hash identifies evidence.

### DERIVED

Artifacts computed only from declared parent inputs.

Examples:
- fetch receipts
- typed acquisition-failure receipts
- Gate-1 receipts
- claims
- policy-version edges
- knowledge states
- BATTLE receipts

Every DERIVED artifact MUST identify its parent evidence by hash or immutable identifier sufficient for replay.

```text
DERIVED != SOURCE
DERIVED MAY NOT REWRITE INPUT
```

If parent evidence changes, a new derived artifact is required.

### OPTIONAL

Artifacts that may bind or publish an already-complete result but are not required to verify the underlying corpus.

Example:
- Base/EAS witness

```text
OPTIONAL_WITNESS != EVIDENCE_SOURCE
OPTIONAL_WITNESS != INSTITUTIONAL_ENDORSEMENT
```

## 4. Acquisition / verification separation

```text
ACQUISITION_ROLE != VERIFICATION_ROLE
```

Gate 1 MUST operate offline on already-captured corpus inputs. Network access is not required for Gate-1 verification.

A verifier MUST NOT repair, refetch, substitute, normalize, or synthesize missing corpus bytes.

```text
MISSING_INPUT -> FAIL
INVALID_INPUT -> FAIL
NETWORK_UNAVAILABLE -> NOT_A_GATE1_REPAIR_PATH
```

## 5. Failure receipts

Transport failures are first-class DERIVED receipts. They are not corpus rows and do not create synthetic `B_a` objects.

```text
FETCH_FAILURE != MANIFEST_OBSERVATION
FETCH_FAILURE != GATE1_PASS
```

If any required acquisition in the declared scope fails under a fail-closed capture policy:

```text
ACQUISITION_STATUS = HALT_FAIL_CLOSED
MANIFEST_COMPLETION = FALSE
GATE1_PROMOTION = PROHIBITED
```

## 6. Gate-1 promotion firewall

```text
GATE1 != PASS => L2+ PROHIBITED
GATE1 != PASS => L3.6 PROHIBITED
NO H_G1^PASS => BASE_ATTESTATION PROHIBITED
```

Gate 1 verifies the captured bytes and manifest structure. It does not adjudicate policy truth, institutional intent, current authority, or human impact.

## 7. Receipt hashing

`H_manifest` is the SHA-256 digest of the exact manifest bytes supplied to Gate 1.

`H_G1` is the SHA-256 digest of the exact canonical Gate-1 receipt bytes.

To avoid a self-referential hash, `H_G1` MUST NOT be embedded as a field inside the receipt bytes from which `H_G1` is computed. It is emitted externally as a sidecar, CLI result, artifact metadata field, or witness binding.

```text
receipt_bytes -> SHA256 -> H_G1
H_G1 NOT_IN receipt_bytes
```

## 8. No adjacency promotion

```text
VERIFIED(A) + VERIFIED(B) != VERIFIED(A -> B)
```

Every causal/version edge requires its own evidence binding. Missing edge evidence leaves the edge `UNPROVEN`.

## 9. Absence rule

```text
ABSENCE_FROM_CORPUS != EVIDENCE_OF_ABSENCE
```

unless the declared scope contains an explicit completeness claim sufficient to support that inference.

## 10. Authority boundary

```text
COMMITTER != SOURCE != IMPLEMENTER
COMMON VERIFICATION PROTOCOL != COMMON INSTITUTIONAL AUTHORITY
ONCHAIN ATTESTATION != INSTITUTIONAL ENDORSEMENT
```

This directory contract creates no authority and no presumption of truth beyond the bounded evidence and deterministic checks it defines.
