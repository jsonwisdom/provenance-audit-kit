# PUBLIC_REPLAY_MANIFEST_SPEC_v0.1

Status: FROZEN / CYCLE-FREE  
Protocol: `PUBLIC_REPLAY_PROTOCOL_v0.1`

This specification defines the canonical manifest handoff between acquisition and the pure offline Gate-1 verifier. The manifest records admitted observations. It does not contain source bytes, post-manifest immutability evidence, or promotion authority.

## 1. Boundary

```text
ACQUISITION -> CANONICAL MANIFEST -> H_manifest
                                      |
                                      v
                              POST-MANIFEST SEAL
                                      |
                                      v
                                OFFLINE GATE1
```

```text
MANIFEST != RAW BYTES
MANIFEST != IMMUTABILITY BINDING
MANIFEST != GATE1 RECEIPT
MANIFEST_COMPLETE != GATE1_PASS
```

The manifest is an INPUT artifact under `directory-contract.md`. Once created for a capture, its exact bytes are immutable. Any change requires a new manifest artifact and new hash.

## 2. Canonical observation row

Each admitted observation is represented by exactly one JSON object encoded as one JSONL line.

Core canonical fields:

```text
capture_id
scope_id
profile_id
header_ref
H_a
bytes_len
mime_type
observed_at
raw_ref
status_code
url
corpus_admitted
```

Institution profiles MAY require additional fields only when declared before serialization. Undeclared ad hoc fields are prohibited.

Field semantics:

- `capture_id`: immutable acquisition execution identifier.
- `scope_id`: identifier of the declared scope whose required observations this manifest is intended to satisfy.
- `profile_id`: identifier of the institution profile constraining acquisition and verification.
- `header_ref`: reference to the separately retained observed-header artifact.
- `H_a`: lowercase hexadecimal SHA-256 of exact response body bytes `B_a`.
- `bytes_len`: exact byte length of `B_a`.
- `mime_type`: observed content type; it does not redefine the bytes.
- `observed_at`: acquisition observation time, not publication/effective-policy time.
- `raw_ref`: content-addressed raw-object reference `corpus/raw/<H_a>`.
- `status_code`: admitted HTTP response status under the active profile.
- `url`: declared source URL for the observation.
- `corpus_admitted`: MUST be `true` for every manifest row.

A failure receipt is never serialized as a manifest row.

```text
FETCH_FAILURE != MANIFEST_ROW
corpus_admitted = false -> ROW_PROHIBITED
```

## 3. No post-manifest references inside the manifest

A manifest row MUST NOT contain `immutability_evidence_ref`, `H_manifest`, `H_G1`, a seal identifier, or another field whose value can only exist after final manifest bytes are known.

This prevents circular hashing:

```text
MANIFEST -> H_manifest -> EVIDENCE -> evidence_H -> MANIFEST
```

The cycle-free ordering is:

```text
manifest_bytes
-> H_manifest
-> immutability evidence
-> immutability binding
-> Gate1
```

The post-manifest binding is defined by `gate1/immutability/binding-spec.md`.

## 4. Manifest identity domain

One `manifest.jsonl` belongs to exactly one acquisition/scope/profile tuple:

```text
M = (capture_id, scope_id, profile_id)
```

Every row MUST contain the same values.

```text
MIXED_CAPTURE_IDS -> INVALID_MANIFEST
MIXED_SCOPE_IDS -> INVALID_MANIFEST
MIXED_PROFILE_IDS -> INVALID_MANIFEST
```

Because `scope_id` and `profile_id` are inside every row, `H_manifest` binds the interpretation boundary used for scope and profile evaluation.

## 5. Row canonicalization

Every row MUST use the ReceiptOS byte-strict evidence canonicalization profile:

```text
UTF-8, no BOM
object keys sorted lexicographically by Unicode code point
no insignificant whitespace
integer-only numeric values
exactly one LF after each JSON object
```

Equivalent:

```text
canonical_row = ReceiptOS.canonicalize(row) || 0x0A
```

`observed_at` MUST be RFC 3339 UTC ending in `Z`.

Implementations MUST NOT pretty-print, use CRLF, insert a BOM, or silently normalize/rewrite source-derived values after admission.

## 6. File ordering

Rows are sorted by the deterministic total ordering:

```text
(url, observed_at, capture_id, H_a, raw_ref, header_ref)
```

all ascending lexicographically by canonical string value.

Byte-identical rows remain present; observation multiplicity MUST NOT be silently collapsed.

## 7. File canonicalization

```text
manifest_bytes = canonical_row_1 || ... || canonical_row_n
```

A valid manifest MUST:

- contain at least one row;
- contain no blank lines/comments/prefix/suffix;
- end every row, including the final row, with LF;
- contain only admitted rows;
- bind exactly one `capture_id`, `scope_id`, and `profile_id`.

The empty-file SHA-256 MUST NOT be accepted as a successful manifest identity.

## 8. Manifest hash

```text
H_manifest = SHA256(exact canonical manifest.jsonl bytes)
```

Rendered form is lowercase 64-hex.

No path, filename, Git commit, seal object, Gate-1 receipt, transport metadata, or witness is included unless it was already part of the canonical manifest bytes.

```text
SAME manifest_bytes -> SAME H_manifest
DIFFERENT manifest_bytes -> DIFFERENT HASH INPUT
```

## 9. Raw-object binding

For each row `r`:

```text
r.raw_ref = corpus/raw/<r.H_a>
SHA256(read(r.raw_ref)) = r.H_a
len(read(r.raw_ref)) = r.bytes_len
```

The manifest never contains or normalizes `B_a` itself.

Missing objects, hash mismatches, length mismatches, or non-content-addressed raw references are Gate-1 failures.

## 10. Header binding

`header_ref` identifies the separately retained observed-header artifact.

If a profile requires a header digest, that digest must be known before manifest construction and becomes a declared canonical row field.

Headers never change `H_a`, which identifies response body bytes only in v0.1.

## 11. Completion rule

Let `R(S)` be the required URL set declared by the active scope.

```text
MANIFEST_COMPLETION = TRUE
iff
1. every row belongs to the declared scope/profile; AND
2. for every u in R(S), at least one admitted row exists with row.url = u
```

Otherwise:

```text
MANIFEST_COMPLETION = FALSE
GATE1_ELIGIBLE = FALSE
```

Out-of-scope padding cannot manufacture completeness. A required acquisition failure leaves the required admitted row absent.

## 12. Multiplicity and storage deduplication

```text
H_A = H_B
-> raw bytes MAY be stored once
-> both admitted observations remain rows
```

```text
STORAGE_DEDUPLICATION != OBSERVATION_DEDUPLICATION
```

Different URLs or repeated observations may legitimately resolve to the same `H_a`.

## 13. Post-manifest immutability evidence / V06

V06 evidence is never a row field.

After `H_manifest` exists, a storage-seal mechanism may create content-addressed evidence that binds the exact `capture_id` and `H_manifest`. A separate canonical binding then selects that evidence for Gate 1:

```text
immutability/bindings/<H_binding>.json
```

The binding must satisfy `gate1/immutability/binding-spec.md`.

```text
NO VALID IMMUTABILITY BINDING -> V06 FAIL
VALID BINDING != V06 PASS
```

The verifier MUST NOT infer historical no-overwrite behavior from the current snapshot alone.

## 14. Profile extensions

Institution-specific fields may extend rows only when:

- field semantics are declared by the profile;
- type/serialization are deterministic;
- the value is known before manifest construction;
- every verifier for that profile applies the same field set.

```text
PROFILE_EXTENDS_CORE
PROFILE_MAY_NOT_REDEFINE_CORE
```

## 15. Mutation rule

```text
MANIFEST_CREATED -> IMMUTABLE
MANIFEST_EDIT -> PROHIBITED
```

Adding/removing/correcting/reordering/reserializing observations or changing scope/profile produces a new manifest and new `H_manifest`.

A manifest MUST NOT be edited in place to convert incomplete acquisition into complete acquisition or to insert post-manifest seal evidence.

## 16. Gate-1 handoff

The generic offline verifier consumes the declared inputs:

```text
manifest.jsonl
+ corpus/raw/
+ profile
+ immutability/bindings/<H_binding>.json
+ content-addressed immutability evidence/proofs referenced by that binding
```

For the SSA profile:

```text
(manifest + raw + profile=ssa + immutability binding)
-> SSA_GATE1_RECEIPT_v0.1.json
```

Gate 1 recomputes `H_manifest` from exact supplied bytes and `H_binding` from exact supplied binding bytes. Caller-supplied hashes are never trusted without recomputation.

## 17. Promotion firewall

```text
MANIFEST_COMPLETION = TRUE != GATE1_PASS
H_manifest EXISTS != H_G1^PASS EXISTS
V06_PASS != GATE1_PASS
GATE1 != PASS -> L3.6 PROHIBITED
NO H_G1^PASS -> BASE_ATTESTATION PROHIBITED
```

The manifest proves only the canonical observation handoff. Promotion remains exclusively with the complete independent offline Gate-1 conjunction.
