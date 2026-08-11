# PUBLIC_REPLAY_V06_IMMUTABILITY_CONTRACT_v0.1

Status: FROZEN / GIT RESOLVER IMPLEMENTED / REAL-KERNEL INTEGRATION PENDING  
Protocol: `PUBLIC_REPLAY_PROTOCOL_v0.1`  
Gate: `V06`

This contract defines the institution-neutral evidence boundary for proving that a captured public-replay corpus was sealed against in-place overwrite after capture.

```text
CORPUS_STORAGE_SEALED_AGAINST_OVERWRITE
!= SOURCE_NEVER_CHANGED
!= SOURCE_TRUTH
!= DURABILITY_FOREVER
!= AUTHORITY
```

## 1. Current posture

The original generic Gate-1 surface-test freeze gate passed at commit `13701b359f2d66c0bcfa45de49e621026ade3df7`. That receipt remains valid for that exact historical head.

The contract is frozen. A production Git resolver is now implemented, but the verifier/binding surface changed after the original test and therefore requires a new independent test receipt.

```text
CONTRACT_FROZEN = TRUE
GIT_RESOLVER_IMPLEMENTED = TRUE
REAL_KERNEL_INTEGRATION_TEST_WRITTEN = TRUE
REAL_KERNEL_INTEGRATION_RECEIPT = MISSING
CLI_WIRED_TO_GIT_RESOLVER = FALSE
PRODUCTION_V06_PASS = PROHIBITED
PRODUCTION_GATE1_PASS = PROHIBITED
```

The production CLI remains on `UNRESOLVED_IMMUTABILITY_FAIL_CLOSED_v0.1` until the new integration gate passes.

## 2. Cycle-free evidence selection

The canonical manifest MUST NOT contain an evidence reference because the evidence itself binds `H_manifest`.

```text
manifest_bytes
-> H_manifest
-> storage-seal evidence
-> immutability binding
-> Gate1
```

Evidence selection is supplied by the content-addressed post-manifest binding defined in `binding-spec.md`:

```text
immutability/bindings/<H_binding>.json
```

The binding identifies exactly one:

```text
immutability/objects/<evidence_H>.json
```

for v0.1.

```text
VALID_BINDING != V06_PASS
```

## 3. Common evidence fields

Every evidence object binds at least:

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

- `capture_id` equals the manifest capture identity;
- `H_manifest` equals Gate-1's recomputed SHA-256 of exact manifest bytes;
- `prev_H_manifest` is lowercase 64-hex or JSON null;
- `stored_at` is evidence metadata, not verifier wall-clock time;
- `storage_id` identifies the concrete content-addressed preservation state;
- `no_overwrite_attestation_ref` is offline-resolvable and must be mechanically verified.

## 4. Offline resolution

```text
NETWORK = PROHIBITED
CHILD_PROCESS = PROHIBITED
REMOTE_LOOKUP = PROHIBITED
MUTATION = PROHIBITED
```

No resolver may repair, refetch, substitute, or infer missing evidence.

Minimum deterministic failures include:

```text
IMMUTABILITY_REF_MISSING
IMMUTABILITY_REF_INVALID
IMMUTABILITY_REF_UNRESOLVABLE
IMMUTABILITY_PATH_TRAVERSAL
IMMUTABILITY_EVIDENCE_HASH_MISMATCH
IMMUTABILITY_EVIDENCE_NOT_CANONICAL
IMMUTABILITY_EVIDENCE_SCHEMA_INVALID
IMMUTABILITY_EVIDENCE_TYPE_UNKNOWN
IMMUTABILITY_CAPTURE_BINDING_MISMATCH
IMMUTABILITY_MANIFEST_BINDING_MISMATCH
IMMUTABILITY_PARENT_BINDING_MISMATCH
IMMUTABILITY_STORAGE_IDENTITY_MISMATCH
IMMUTABILITY_ATTESTATION_UNRESOLVABLE
IMMUTABILITY_ATTESTATION_INVALID
IMMUTABILITY_EVIDENCE_INSUFFICIENT
IMMUTABILITY_RUNTIME_PROHIBITED_OPERATION
```

## 5. Sufficiency predicate

For evidence object `E` and recomputed manifest hash `H_manifest`:

```text
V06(E) = PASS
iff
1. E resolves offline from declared artifacts; AND
2. SHA256(canonical_E_bytes) = evidence_H from its content-addressed ref; AND
3. E.capture_id = manifest.capture_id; AND
4. E.H_manifest = recomputed H_manifest; AND
5. evidence-type-specific integrity checks PASS; AND
6. changing sealed bytes requires changing the storage/content identity; AND
7. no_overwrite_attestation_ref verifies under that mechanism.
```

Presence of fields never self-certifies sufficiency.

## 6. Evidence types

v0.1 registers:

```text
GIT_COMMIT_CHAIN_v0.1
WORM_STORE_ATTESTATION_v0.1
IPFS_PIN_v0.1
```

Only the Git resolver is implemented in the current branch. WORM and IPFS remain schema/contracts only.

### 6.1 Git commit chain

Git evidence uses exact content-addressed proof envelopes for native commit/tree/blob object bytes.

The resolver MUST recompute native Git object IDs without invoking `git` and prove that:

- the declared commit hashes correctly;
- its root tree hashes correctly;
- the root tree contains exact `manifest.jsonl` bytes;
- the root tree contains every exact raw object named by the manifest;
- branch names are ignored as evidence;
- when `prev_H_manifest` is non-null, a selected actual parent commit contains prior manifest bytes whose SHA-256 equals `prev_H_manifest`;
- the no-overwrite attestation matches the recomputed object chain.

```text
GIT_BRANCH_NAME != IMMUTABILITY_EVIDENCE
```

### 6.2 WORM store attestation

WORM remains unimplemented. A future resolver must verify exact attestation bytes and required key/signature material offline.

A vendor name, screenshot, unsigned JSON, or policy statement is insufficient.

### 6.3 IPFS pin

IPFS remains unimplemented.

```text
CONTENT_ADDRESS_IMMUTABILITY != PIN_AVAILABILITY
```

A pin receipt alone is insufficient; a future resolver must have local CID-recomputable blocks/CAR evidence.

## 7. Chain rule

When `prev_H_manifest` is non-null:

```text
current commit -> selected parent commit
selected parent tree -> previous manifest blob
SHA256(previous manifest bytes) = prev_H_manifest
```

A broken or ambiguous parent link fails V06.

`prev_H_manifest = null` declares no prior manifest link for the V06 chain; it does not make a mutable branch ref authoritative.

## 8. v0.1 multiplicity

The post-manifest binding selects exactly one active evidence object in v0.1.

```text
MULTIPLE EVIDENCE OBJECTS WITH UNDEFINED COMPOSITION = PROHIBITED
```

A later protocol version may define explicit evidence composition.

## 9. Resolver result

A conforming resolver returns:

```text
{
  V06: PASS|FAIL,
  reason: TYPED_REASON,
  evidence_H: <64-lowercase-hex|null>
}
```

PASS requires a verified `evidence_H`.

Gate-1 additionally binds the active resolver's implementation SHA-256 into the canonical Gate-1 receipt.

## 10. Authority boundary

```text
V06_PASS = STORAGE_IMMUTABILITY_EVIDENCE_PASS
V06_PASS != SOURCE_TRUTH
V06_PASS != POLICY_CORRECTNESS
V06_PASS != GATE1_PASS
V06_PASS != L3.6
V06_PASS != BASE_ATTESTATION
```

Only V01-V08 together may produce `H_G1^PASS`.

## 11. Historical freeze receipt

The original contract-freeze receipt remains retained under:

```text
gate1/test-receipts/13701b359f2d66c0bcfa45de49e621026ade3df7/
```

with:

```text
HEAD_SHA=13701b359f2d66c0bcfa45de49e621026ade3df7
TEST_FILE_SHA256=14c6ddb10797c1e0977f5a04651ea7420d517d468ccdad675f004021fdc8caed
PYTHON=Python 3.12.3
TEST_EXIT=0
TEST_RESULT=PASS
RAW_LOG_SHA256=37d8a0769d6c800296764c21f8e08feca52d770d400afabe65713604062cf749
```

That receipt authorized contract freeze only. The new resolver/verifier head requires a new independent receipt before production V06 may be wired or trusted.
