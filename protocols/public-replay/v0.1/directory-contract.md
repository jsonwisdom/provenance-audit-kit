# PUBLIC_REPLAY_DIRECTORY_CONTRACT_v0.1

Status: FROZEN / CYCLE-FREE SEAL LAYOUT  
Protocol: `PUBLIC_REPLAY_PROTOCOL_v0.1`

This contract defines where public-replay artifacts live and which classes are INPUT, DERIVED, or OPTIONAL.

## 1. Layer separation

```text
PROTOCOL != INSTITUTION != CORPUS != KNOWLEDGE != WITNESS
```

The protocol defines reusable rules. Institution profiles specialize scope/transport. Corpus instances contain observed evidence. Knowledge artifacts derive only after Gate-1 PASS. Witnesses bind already-created receipts and never create authority.

## 2. Canonical layout

```text
protocols/public-replay/v0.1/
  directory-contract.md
  acquisition-spec.md
  manifest-spec.md
  profiles/
    <institution>/
      schemas/
  gate1/
    README.md
    verifier.py
    cli.py
    immutability/
      binding-spec.md
      immutability-contract.md
      resolver-interface.md
      schemas/

audits/public-institutions/
  <institution>/
    <corpus_id>/
      scope/                         # INPUT
      acquisition/                   # INPUT config/metadata; no verifier authority
      corpus/
        raw/                         # INPUT exact response bytes, content-addressed
        headers/                     # INPUT observed response headers
      manifests/                     # INPUT canonical observation manifests
      immutability/                  # DERIVED POST-MANIFEST VERIFICATION INPUTS
        bindings/                    # content-addressed H_manifest -> evidence selection
        objects/                     # content-addressed mechanism evidence
        proofs/                      # content-addressed offline proof envelopes
        attestations/                # content-addressed mechanically checked assertions
      receipts/
        fetch/                       # DERIVED acquisition event
        failures/                    # DERIVED failed acquisition event
        gate1/                       # DERIVED only by offline verifier
      knowledge/
        claims/                      # DERIVED; Gate-1 PASS required
        policy-graph/                # DERIVED; Gate-1 PASS required
        states/                      # DERIVED L3.6; Gate-1 PASS required
        divergences/                 # DERIVED
        contradiction-tests/         # DERIVED
        battles/                     # DERIVED
      witnesses/
        base/                        # OPTIONAL; H_G1^PASS required
```

## 3. INPUT

INPUT is observed or operator-declared material that exists before post-manifest sealing.

Examples:

- declared scope/profile;
- exact public response bytes `B_a`;
- observed response headers;
- canonical `manifest.jsonl`.

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
SHA256(read(path(B_a))) = H_a
```

A URL locates an observation. A hash identifies evidence.

## 4. DERIVED

DERIVED artifacts are computed from declared parent identities and MUST NOT rewrite INPUT.

Examples:

- fetch receipts;
- typed acquisition-failure receipts;
- post-manifest immutability evidence/proofs/attestations;
- immutability binding;
- Gate-1 receipt;
- claims/policy graph/knowledge state/BATTLE receipts.

Every DERIVED artifact identifies parent evidence by hash or another replay-sufficient immutable identity.

```text
DERIVED != SOURCE
DERIVED MAY NOT REWRITE INPUT
```

### 4.1 Post-manifest seal artifacts

V06 seal evidence is DERIVED only after final manifest bytes exist:

```text
manifest_bytes
-> H_manifest
-> immutability/objects/<evidence_H>.json
-> immutability/bindings/<H_binding>.json
```

The binding and evidence are inputs to Gate 1, but they remain DERIVED artifact classes because they are created from already-frozen manifest/corpus inputs.

```text
GATE1_INPUT != ACQUISITION_INPUT_ONLY
```

A manifest MUST NOT be edited to point to its own post-manifest seal evidence.

## 5. OPTIONAL

OPTIONAL artifacts publish or witness an already-complete result but are not required to verify the corpus.

Example: Base/EAS witness.

```text
OPTIONAL_WITNESS != EVIDENCE_SOURCE
OPTIONAL_WITNESS != INSTITUTIONAL_ENDORSEMENT
```

## 6. Acquisition / sealing / verification separation

```text
ACQUISITION_ROLE != VERIFICATION_ROLE
SEALING_PHASE != VERIFICATION_ROLE
```

The sealing phase may create content-addressed DERIVED proof artifacts after `H_manifest` exists, but may not mutate the manifest or claim Gate-1 PASS.

Gate 1 operates offline on already-materialized manifest/raw/profile/binding/evidence inputs.

A verifier MUST NOT repair, refetch, substitute, normalize, or synthesize missing bytes/evidence.

```text
MISSING_INPUT -> FAIL
INVALID_INPUT -> FAIL
NETWORK_UNAVAILABLE -> NOT_A_GATE1_REPAIR_PATH
```

## 7. Failure receipts

Transport failures are first-class DERIVED receipts. They are not corpus rows and create no synthetic `B_a`.

```text
FETCH_FAILURE != MANIFEST_OBSERVATION
FETCH_FAILURE != GATE1_PASS
```

Required acquisition failure keeps manifest completion false and promotion prohibited.

## 8. Gate-1 promotion firewall

```text
GATE1 != PASS => L2+ PROHIBITED
GATE1 != PASS => L3.6 PROHIBITED
NO H_G1^PASS => BASE_ATTESTATION PROHIBITED
```

Gate 1 verifies byte/manifests/seal integrity. It does not adjudicate policy truth, intent, current authority, or human impact.

## 9. Hash domains

```text
H_manifest = SHA256(exact canonical manifest bytes)
H_binding = SHA256(exact canonical immutability binding bytes)
evidence_H = SHA256(exact canonical evidence bytes)
H_G1 = SHA256(exact canonical Gate-1 receipt bytes)
```

`H_G1` MUST NOT be embedded in the receipt bytes it hashes.

```text
receipt_bytes -> SHA256 -> H_G1
H_G1 NOT_IN receipt_bytes
```

The Gate-1 receipt binds `H_manifest`, `H_binding`, active evidence refs, verifier source identity, resolver source identity, and ReceiptOS kernel source identities.

## 10. No adjacency promotion

```text
VERIFIED(A) + VERIFIED(B) != VERIFIED(A -> B)
```

Every causal/version edge requires its own evidence binding. Missing edge evidence leaves the edge `UNPROVEN`.

## 11. Absence rule

```text
ABSENCE_FROM_CORPUS != EVIDENCE_OF_ABSENCE
```

unless an explicit completeness claim supports that inference.

## 12. Authority boundary

```text
COMMITTER != SOURCE != IMPLEMENTER
COMMON VERIFICATION PROTOCOL != COMMON INSTITUTIONAL AUTHORITY
ONCHAIN ATTESTATION != INSTITUTIONAL ENDORSEMENT
```

This directory contract creates no authority beyond the bounded evidence and deterministic checks it defines.
