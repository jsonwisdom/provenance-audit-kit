# PUBLIC_REPLAY_V06_IMMUTABILITY_CONTRACT_v0.1

Status: FROZEN DRAFT / TEST_EXECUTION_PENDING  
Protocol: `PUBLIC_REPLAY_PROTOCOL_v0.1`  
Gate: `V06`

This contract defines the institution-neutral evidence boundary for proving that a captured public-replay corpus was sealed against in-place overwrite after capture. It does not prove source truth, source continuity, publication time, policy validity, availability forever, or institutional authority.

```text
CORPUS_STORAGE_SEALED_AGAINST_OVERWRITE
!= SOURCE_NEVER_CHANGED
!= SOURCE_TRUTH
!= DURABILITY_FOREVER
!= AUTHORITY
```

## 1. Production precondition

Until an implementation conforms to this contract and independent Gate-1 tests execute successfully:

```text
PRODUCTION_V06_PASS = PROHIBITED
PRODUCTION_GATE1_PASS = PROHIBITED
```

The current production resolver remains `UNRESOLVED_IMMUTABILITY_FAIL_CLOSED_v0.1`.

## 2. Evidence reference

Every non-null `immutability_evidence_ref` MUST be a content-addressed repository-relative reference:

```text
immutability/objects/<evidence_H>.json
```

where:

```text
evidence_H = SHA256(exact canonical evidence file bytes)
```

The evidence file MUST be UTF-8, no BOM, ReceiptOS byte-strict canonical JSON, exactly one JSON object followed by LF.

A mutable alias, branch name, URL, service dashboard, or un-hashed pathname is not sufficient evidence.

## 3. Common evidence fields

Every evidence object MUST bind at least:

```text
schema
capture_id
H_manifest
prev_H_manifest
stored_at
storage_id
no_overwrite_attestation_ref
```

Rules:

- `capture_id` MUST equal the manifest binding tuple capture identifier.
- `H_manifest` MUST equal Gate-1's recomputed manifest SHA-256.
- `prev_H_manifest` is either lowercase 64-hex or JSON null for a declared genesis seal.
- `stored_at` is evidence metadata only; it does not enter the Gate-1 receipt as wall-clock verifier time.
- `storage_id` identifies the concrete preservation object/commit/CID/version being verified.
- `no_overwrite_attestation_ref` MUST itself be offline-resolvable or be a self-contained cryptographic assertion inside the same content-addressed evidence bundle.

## 4. Offline resolution

V06 may consume only artifacts already supplied to the verifier's declared input boundary.

```text
NETWORK = PROHIBITED
CHILD_PROCESS = PROHIBITED
REMOTE_LOOKUP = PROHIBITED
```

Resolution failure is deterministic:

```text
null ref -> V06 FAIL / IMMUTABILITY_REF_MISSING
unresolvable ref -> V06 FAIL / IMMUTABILITY_REF_UNRESOLVABLE
hash mismatch -> V06 FAIL / IMMUTABILITY_EVIDENCE_HASH_MISMATCH
schema/type mismatch -> V06 FAIL / IMMUTABILITY_EVIDENCE_SCHEMA_INVALID
manifest binding mismatch -> V06 FAIL / IMMUTABILITY_MANIFEST_BINDING_MISMATCH
insufficient no-overwrite proof -> V06 FAIL / IMMUTABILITY_EVIDENCE_INSUFFICIENT
```

No resolver may repair, refetch, substitute, or infer missing evidence.

## 5. Sufficiency rule

For an evidence object `E` and manifest hash `H_manifest`:

```text
V06(E) = PASS
iff
1. E is offline-resolvable from committed artifacts; AND
2. SHA256(canonical_E_bytes) = evidence_H from its reference; AND
3. E.capture_id matches the manifest capture_id; AND
4. E.H_manifest = recomputed H_manifest; AND
5. E's evidence-type-specific integrity checks PASS; AND
6. the preservation mechanism proves byte identity cannot be changed in place without changing its content/storage identity; AND
7. no_overwrite_attestation_ref is verified sufficient under that mechanism.
```

Presence of a field or reference never auto-passes V06.

## 6. Evidence types

v0.1 registers three evidence types:

```text
GIT_COMMIT_CHAIN_v0.1
WORM_STORE_ATTESTATION_v0.1
IPFS_PIN_v0.1
```

Each type has its own schema under `immutability/schemas/`.

### 6.1 Git commit chain

Git evidence may prove that exact manifest/corpus identities were sealed into content-addressed Git objects and that a declared child commit descends from the declared parent commit.

It does NOT prove that a mutable branch ref was never force-moved. Branch names are advisory only; object IDs and parent relationships are the evidence.

PASS therefore requires offline availability of the referenced commit/tree/blob evidence sufficient to recompute or verify the bound identities.

### 6.2 WORM store attestation

WORM evidence may prove object-lock / write-once retention semantics only when the exact attestation bytes and all required signature/key material are available offline and verify against the exact `H_manifest` and `storage_id`.

A vendor name, console screenshot, unsigned JSON, or policy statement alone is insufficient.

### 6.3 IPFS pin

IPFS evidence proves content-addressed identity, not permanent availability.

A pin receipt alone is insufficient. PASS requires local evidence sufficient to recompute the declared CID/root from committed bytes (for example a committed CAR/block set) and bind that root to the exact `H_manifest`.

```text
CONTENT_ADDRESS_IMMUTABILITY != PIN_AVAILABILITY
```

## 7. Chain rule

When `prev_H_manifest` is non-null, the evidence MUST provide an offline-verifiable linkage showing that the new sealed state explicitly references the prior manifest identity.

```text
H_manifest[n] -> prev_H_manifest = H_manifest[n-1]
```

A broken, missing, or ambiguous parent link fails V06 for chain-based evidence.

Genesis is explicit:

```text
prev_H_manifest = null
```

Null parent means genesis only; it must never be inferred from missing evidence.

## 8. Multiplicity

Multiple manifest rows may reference the same immutability evidence object when that object seals the entire manifest/corpus state.

Multiple evidence objects may also support one manifest. V06 passes only if the active resolver contract declares how they compose and every required component verifies.

```text
MORE_EVIDENCE != AUTOMATIC_PASS
```

## 9. Production resolver result

A conforming resolver returns a deterministic result equivalent to:

```text
{
  "V06": "PASS|FAIL",
  "reason": "TYPED_REASON",
  "evidence_H": "<64-lowercase-hex|null>"
}
```

The resolver MUST NOT return `PASS` without a verified `evidence_H`.

## 10. Authority boundary

```text
V06_PASS = STORAGE_IMMUTABILITY_EVIDENCE_PASS
V06_PASS != SOURCE_TRUTH
V06_PASS != POLICY_CORRECTNESS
V06_PASS != L3.6
V06_PASS != BASE_ATTESTATION
```

Only the full Gate-1 conjunction may produce `H_G1^PASS`, and only a later authorized witness step may use that receipt.

## 11. Freeze gate

This draft may be promoted from `TEST_EXECUTION_PENDING` only after the existing `gate1/tests/test_gate1_surface.py` is executed in an independent local environment and its raw result is retained. Until then, no production resolver implementation is authorized.
