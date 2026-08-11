# PUBLIC_REPLAY_MANIFEST_SPEC_v0.1

Status: FROZEN DRAFT  
Protocol: `PUBLIC_REPLAY_PROTOCOL_v0.1`

This specification defines the canonical manifest handoff between acquisition and the pure offline Gate-1 verifier. The manifest records admitted observations. It does not contain source bytes, does not repair acquisition failures, and does not itself authorize promotion.

## 1. Boundary

```text
ACQUISITION -> CANONICAL MANIFEST -> OFFLINE GATE1
```

```text
MANIFEST != RAW BYTES
MANIFEST != GATE1 RECEIPT
MANIFEST_COMPLETE != GATE1_PASS
```

The manifest is an INPUT artifact under `directory-contract.md`. Once created for a capture, its exact bytes are immutable. Any change requires a new manifest artifact and new hash.

## 2. Canonical observation row

Each admitted observation is represented by exactly one JSON object encoded as one JSONL line.

Minimum canonical fields:

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
immutability_evidence_ref
```

Institution profiles MAY require additional fields. Additional fields MUST be declared by the active profile before serialization; undeclared ad hoc fields are prohibited.

Field semantics:

- `capture_id`: immutable acquisition execution identifier.
- `scope_id`: immutable identifier of the declared scope whose required observations this manifest is intended to satisfy.
- `profile_id`: immutable identifier of the institution profile that constrained acquisition and later verification.
- `header_ref`: immutable reference to the separately stored observed-header artifact.
- `H_a`: lowercase hexadecimal SHA-256 digest of the exact response body bytes `B_a`.
- `bytes_len`: exact byte length of `B_a`.
- `mime_type`: observed media/content type as recorded by acquisition; it does not redefine the bytes.
- `observed_at`: acquisition observation timestamp; it is not publication or effective-policy time.
- `raw_ref`: content-addressed raw-object reference, canonically `corpus/raw/<H_a>` unless the corpus contract declares an equivalent rooted path.
- `status_code`: admitted HTTP response status under the active institution profile.
- `url`: declared source URL for the observation.
- `corpus_admitted`: MUST be `true` for every manifest row.
- `immutability_evidence_ref`: immutable reference used by Gate-1 V06, or JSON `null` when acquisition produced no sufficient immutability evidence.

```text
immutability_evidence_ref = null -> V06 MUST FAIL
```

A failure receipt is never serialized as a manifest row.

```text
FETCH_FAILURE != MANIFEST_ROW
corpus_admitted = false -> ROW_PROHIBITED
```

## 3. Manifest identity domain

One `manifest.jsonl` belongs to exactly one acquisition/scope/profile tuple:

```text
M = (capture_id, scope_id, profile_id)
```

Every row in the manifest MUST contain the same `capture_id`, `scope_id`, and `profile_id` values.

```text
MIXED_CAPTURE_IDS -> INVALID_MANIFEST
MIXED_SCOPE_IDS -> INVALID_MANIFEST
MIXED_PROFILE_IDS -> INVALID_MANIFEST
```

Because `scope_id` and `profile_id` are inside every canonical row, `H_manifest` cryptographically binds the manifest bytes to the interpretation boundary under which completeness and profile rules are evaluated.

```text
SAME OBSERVATION BYTES + DIFFERENT SCOPE/PROFILE
-> DIFFERENT manifest_bytes
-> DIFFERENT H_manifest
```

## 4. Row canonicalization

Every row MUST be serialized deterministically as UTF-8 JSON with:

```text
object keys: lexicographic ascending order by Unicode code point
encoding: UTF-8, no BOM
whitespace: none outside JSON string values
line ending: LF (`\n`)
line termination: exactly one LF after every row
```

Equivalent illustrative rule:

```text
canonical_row = UTF8(JSON_SORTED_KEYS_COMPACT(row)) + 0x0A
```

Numbers MUST be serialized as JSON integers for integer fields. Timestamps and hashes are strings. `immutability_evidence_ref` is either a non-empty string or JSON `null`.

`observed_at` MUST use an RFC 3339 UTC representation ending in `Z`. Equivalent offset spellings such as `+00:00` are not canonical for this protocol version.

Implementations MUST NOT pretty-print, insert insignificant spaces, use CRLF, emit a UTF-8 BOM, or reorder keys differently.

## 5. File ordering

`manifest.jsonl` is the byte concatenation of all canonical admitted rows in a deterministic total order.

Primary ordering key:

```text
url ASC
```

To remove ambiguity when the same URL has multiple observations, ties MUST be resolved by:

```text
observed_at ASC
capture_id ASC
H_a ASC
raw_ref ASC
header_ref ASC
```

Therefore the canonical ordering tuple is:

```text
(url, observed_at, capture_id, H_a, raw_ref, header_ref)
```

using lexicographic ascending comparison of the canonical string values.

If two rows are byte-identical after canonicalization, both rows remain present. Their multiplicity is evidence of multiple admitted observations and MUST NOT be silently collapsed.

## 6. File canonicalization

Canonical manifest bytes are:

```text
manifest_bytes = canonical_row_1 || canonical_row_2 || ... || canonical_row_n
```

where rows are sorted by the total ordering rule above.

A valid non-empty manifest MUST:

- contain at least one row;
- contain no blank lines;
- contain no comments;
- contain no non-JSON prefix/suffix;
- terminate the final row with LF;
- contain only rows with `corpus_admitted = true`;
- contain exactly one `capture_id` value;
- contain exactly one `scope_id` value;
- contain exactly one `profile_id` value.

For a successful capture:

```text
manifest_bytes != empty_bytes
```

The empty-file SHA-256 value MUST NOT be accepted as a successful manifest hash.

## 7. Manifest hash

`H_manifest` is defined only over the exact canonical `manifest.jsonl` bytes:

```text
H_manifest = SHA256(manifest_bytes)
```

The hash MUST be lowercase hexadecimal when rendered as text.

No path, filename, Git commit, receipt wrapper, transport metadata, or Base witness is included in `H_manifest` unless those bytes are themselves fields inside canonical manifest rows under this specification.

```text
SAME manifest_bytes -> SAME H_manifest
DIFFERENT manifest_bytes -> RECOMPUTE H_manifest
```

## 8. Raw-object binding

For every manifest row `r`:

```text
r.raw_ref = corpus/raw/<r.H_a>
SHA256(read(r.raw_ref)) = r.H_a
len(read(r.raw_ref)) = r.bytes_len
```

The manifest does not contain or normalize `B_a`; it binds to the exact content-addressed raw object.

A missing object, mismatched hash, mismatched byte length, or non-content-addressed raw reference is a Gate-1 failure condition.

## 9. Header binding

`header_ref` MUST identify an immutable observed-header artifact retained separately from `B_a`.

The active acquisition/profile specification MAY require an additional header digest field. If required, that field becomes part of the canonical row and is therefore covered by `H_manifest`.

Headers never change `H_a`, which identifies response body bytes only in v0.1.

## 10. Completion rule

The active scope MUST distinguish required observations from non-required/preflight observations before acquisition starts.

Let `R(S)` be the set of required source URLs declared by the `scope_id` bound into the manifest.

```text
MANIFEST_COMPLETION = TRUE
iff
1. every row belongs to the declared scope/profile boundary; AND
2. for every u in R(S), at least one canonical row exists where:
     row.url = u
     AND row.scope_id = S
     AND row.corpus_admitted = true
```

Otherwise:

```text
MANIFEST_COMPLETION = FALSE
GATE1_ELIGIBLE = FALSE
```

A row whose URL is not admitted by the declared scope is invalid; extra out-of-scope rows cannot be used to manufacture completeness.

A typed acquisition failure for any required URL is sufficient to keep manifest completion false under a fail-closed capture policy.

A non-required preflight artifact MUST NOT satisfy a required scope URL and MUST NOT be inserted into the dataset manifest unless the scope explicitly declares it as an admitted dataset observation.

## 11. Multiplicity and deduplication

Content-addressed storage deduplication and observation multiplicity are separate concerns.

```text
H_A = H_B
-> raw bytes MAY be stored once
-> both admitted observations MUST remain represented as rows
```

Two different URLs may bind to the same `H_a`. The manifest preserves both observations.

Repeated observations of the same URL may also bind to the same `H_a`; each admitted observation remains a row.

```text
STORAGE_DEDUPLICATION != OBSERVATION_DEDUPLICATION
```

## 12. Immutability evidence / V06

Every row MUST carry `immutability_evidence_ref` as either:

```text
non-empty immutable reference
OR
null
```

The presence of a non-null reference does not automatically prove V06; the generic verifier must validate sufficiency under the verification contract.

A null value forces the V06 outcome:

```text
exists row where immutability_evidence_ref = null
-> V06 = FAIL
-> GATE1_STATUS = FAIL
```

The verifier MUST NOT infer historical no-overwrite behavior from the current raw snapshot alone.

## 13. Scope/profile extensions

Institution-specific profile fields may extend the canonical row only when all of the following are true:

- field name and semantics are declared by the profile;
- field type is deterministic;
- canonical serialization follows this specification;
- the field is known before manifest construction;
- all verifiers for that profile apply the same field set.

Profile extensions may constrain a manifest. They may not weaken core fields or core canonicalization rules.

```text
PROFILE_EXTENDS_CORE
PROFILE_MAY_NOT_REDEFINE_CORE
```

## 14. Mutation rule

After canonical `manifest.jsonl` bytes are emitted for a capture:

```text
MANIFEST_CREATED -> IMMUTABLE
MANIFEST_EDIT -> PROHIBITED
```

If an observation is added, removed, corrected, reordered, reserialized, assigned to another scope, or interpreted under another profile, that result is a new manifest artifact with a newly computed `H_manifest`.

A manifest MUST NOT be edited in place to convert an incomplete capture into a complete one.

## 15. Gate-1 handoff

The generic offline verifier consumes:

```text
manifest.jsonl
+ content-addressed raw objects
+ active institution profile
+ declared scope/completeness evidence
+ immutability evidence references
```

Before V01-V08, the verifier MUST confirm that the externally supplied active `scope_id` and `profile_id` exactly equal the values bound into every manifest row. A mismatch is fail-closed.

For the SSA profile:

```text
(manifest.jsonl + raw/ + profile=ssa)
-> SSA_GATE1_RECEIPT_v0.1.json
```

The verifier MUST recompute `H_manifest` from the exact supplied manifest bytes and MUST NOT trust a caller-supplied digest without recomputation.

## 16. Promotion firewall

```text
MANIFEST_COMPLETION = TRUE != GATE1_PASS
H_manifest EXISTS != H_G1^PASS EXISTS
GATE1 != PASS -> L3.6 PROHIBITED
NO H_G1^PASS -> BASE_ATTESTATION PROHIBITED
```

The manifest proves only the canonical observation handoff. Promotion authority remains exclusively with the independent offline Gate-1 evaluation under V01-V08.
