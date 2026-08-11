# PUBLIC_REPLAY_IMMUTABILITY_BINDING_SPEC_v0.1

Status: FROZEN / CYCLE-FREE V06 INPUT BOUNDARY  
Protocol: `PUBLIC_REPLAY_PROTOCOL_v0.1`  
Gate: `V06`

This specification separates the immutable acquisition manifest from the post-manifest storage-seal evidence required by V06.

## 1. Cycle firewall

The manifest MUST NOT contain an immutability evidence reference when that evidence binds `H_manifest`.

Otherwise the construction becomes circular:

```text
H_manifest
-> evidence.H_manifest
-> evidence_H
-> manifest.immutability_evidence_ref
-> H_manifest
```

Therefore:

```text
MANIFEST_BYTES ARE FINAL FIRST
-> H_manifest IS COMPUTED
-> IMMUTABILITY EVIDENCE IS CREATED
-> IMMUTABILITY BINDING IS CREATED
-> GATE1 VERIFIES ALL OF THEM OFFLINE
```

```text
MANIFEST != IMMUTABILITY_BINDING
IMMUTABILITY_BINDING != IMMUTABILITY_EVIDENCE
```

## 2. Binding object

Exactly one v0.1 binding object is supplied to Gate 1 for one manifest:

```json
{
  "schema": "PUBLIC_REPLAY_IMMUTABILITY_BINDING_v0.1",
  "capture_id": "<capture id>",
  "H_manifest": "<64 lowercase hex>",
  "evidence_ref": "immutability/objects/<evidence_H>.json"
}
```

The file MUST be ReceiptOS byte-strict canonical JSON encoded as UTF-8 with no BOM and exactly one trailing LF.

## 3. Content address

The binding itself is content-addressed:

```text
immutability/bindings/<H_binding>.json
```

where:

```text
H_binding = SHA256(exact canonical binding file bytes)
```

The verifier MUST recompute `H_binding`; it MUST NOT trust the filename alone.

## 4. Required bindings

Gate 1 MUST prove:

```text
binding.capture_id = manifest.capture_id
binding.H_manifest = SHA256(exact manifest.jsonl bytes)
binding.evidence_ref resolves offline
```

Any mismatch is V06 FAIL.

## 5. Temporal order

The binding is necessarily post-manifest because it names `H_manifest`.

```text
ACQUISITION_COMPLETE
-> MANIFEST_FINAL
-> H_manifest
-> STORAGE_SEAL_EVIDENCE
-> IMMUTABILITY_BINDING
-> OFFLINE_GATE1
```

This ordering does not mutate the manifest and does not grant acquisition verifier authority.

## 6. v0.1 multiplicity

v0.1 allows exactly one active `evidence_ref` per binding. Evidence-type composition is deferred until a later version with an explicit composition rule.

```text
MULTIPLE_EVIDENCE_OBJECTS_WITH_UNDEFINED_COMPOSITION = PROHIBITED
```

## 7. Gate-1 receipt binding

The canonical Gate-1 receipt MUST include:

```text
immutability_binding_sha256 = H_binding
immutability_evidence_refs = [binding.evidence_ref]
```

This binds the V06 evidence-selection input into `H_G1` without embedding `H_G1` into itself.

## 8. Failure rules

```text
binding missing -> V06 FAIL / IMMUTABILITY_BINDING_MISSING
binding noncanonical -> V06 FAIL / IMMUTABILITY_BINDING_NOT_CANONICAL
binding hash/path mismatch -> V06 FAIL / IMMUTABILITY_BINDING_HASH_MISMATCH
capture mismatch -> V06 FAIL / IMMUTABILITY_CAPTURE_BINDING_MISMATCH
manifest mismatch -> V06 FAIL / IMMUTABILITY_MANIFEST_BINDING_MISMATCH
evidence unresolved/insufficient -> V06 FAIL / resolver typed reason
```

No fallback to a row-level reference is permitted.

## 9. Authority boundary

```text
VALID_BINDING != V06_PASS
V06_PASS != GATE1_PASS
GATE1_PASS != L3.6
GATE1_PASS != BASE_ATTESTATION
```

The binding proves only which content-addressed V06 evidence object is being evaluated against which exact manifest.
