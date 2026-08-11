# PUBLIC_REPLAY_ACQUISITION_SPEC_v0.1

Status: FROZEN / CYCLE-FREE HANDOFF  
Protocol: `PUBLIC_REPLAY_PROTOCOL_v0.1`

This specification defines the acquisition boundary for public-institution replay corpora. Acquisition observes and stores public response bytes. It does not verify Gate 1, derive knowledge state, adjudicate policy, or create institutional authority.

## 1. Role separation

```text
ACQUISITION_ROLE != VERIFICATION_ROLE
LOCAL_ACQUISITION != GITHUB_VERIFICATION
```

`LOCAL_ACQUISITION` means an acquisition execution role independent from the verifier. It does not require a particular device or physical location. A laptop, Cloud Shell, controlled VM, or other operator-controlled environment may perform acquisition if it satisfies this specification.

The same execution event MUST NOT both acquire a corpus and act as the independent Gate-1 verifier for that corpus.

GitHub Actions MAY verify already-imported corpus inputs offline. GitHub Actions MUST NOT be required to originate the bytes it verifies.

## 2. Allowed acquisition environment

An allowed acquisition environment MUST:

- have ordinary network access to the declared public source;
- use only public, unauthenticated source surfaces declared by the institution profile and scope;
- declare acquisition client/version;
- send a non-empty truthful project User-Agent;
- declare a non-empty operator/project contact;
- declare request timeout and maximum request rate;
- record redirect behavior and final effective URL;
- preserve exact response body bytes;
- preserve observed response headers needed for replay/provenance;
- use write-if-absent semantics for content-addressed raw objects;
- halt rather than repair a required acquisition failure.

The acquisition environment MUST NOT:

- authenticate to private claimant/account surfaces;
- use session credentials to expand public scope;
- bypass access control, WAF, CAPTCHA, robots policy, rate limit, or source restriction;
- rotate proxies or spoof browser identity to defeat source controls;
- synthesize, normalize, reconstruct, or substitute missing response bytes;
- treat cached/search-engine/third-party bytes as source bytes unless that third party is explicitly the declared source.

```text
SOURCE_DENIES_REQUEST -> TYPED_FAILURE
SOURCE_DENIES_REQUEST != BYPASS_AUTHORIZATION
```

## 3. Institution profile obligations

Each institution profile MUST declare at minimum:

```text
profile_id
allowed_scheme
allowed_hosts[]
required_user_agent_format
required_contact_format
max_request_rate
request_timeout
redirect_policy
success_http_status
private_or_authenticated_surfaces_prohibited = true
```

A redirect may be followed only when allowed by profile; redirect chain and final effective URL remain acquisition evidence.

Profile values constrain acquisition. They do not grant permission or override source controls.

## 4. Capture identity

Every acquisition execution creates a new immutable `capture_id` before the first request.

Logical capture root:

```text
capture/<capture_id>/
  raw/
  headers/
  receipts/
    fetch/
    failures/
  session/
```

The institution corpus layout may map these logical classes into canonical directory paths, but artifact semantics remain unchanged.

```text
CAPTURE_CREATED -> APPEND_ONLY
CAPTURE_REWRITE -> PROHIBITED
```

## 5. Successful observation

For observation `a`, let `B_a` be exact final-response body bytes.

```text
H_a = SHA256(B_a)
path(B_a) = corpus/raw/<H_a>
SHA256(read(path(B_a))) = H_a
```

A successful observation retains at minimum:

```text
source_url
effective_url
captured_at
http_status
content_type
byte_length
H_a
raw_object
response_headers_sha256
headers_object
capture_id
acquisition_client
request_user_agent
request_contact
request_timeout
request_rate_limit
```

```text
T_capture != T_publication != T_effective
```

The response body is byte-for-byte authoritative for this observation. Decoding/parsing/normalization are DERIVED artifacts and never replace `B_a`.

## 6. Response headers

Observed response headers remain separate from body bytes.

Headers do not alter `H_a`. If serialized, their serialization is declared and independently hashed.

## 7. Write-if-absent rule

```text
if corpus/raw/<H_a> missing:
    CREATE_EXCLUSIVE(B_a)
else if read(existing) == B_a:
    REUSE_OBJECT
else:
    MUTATION_PROHIBITED / HALT
```

Observation multiplicity is preserved even when storage deduplicates identical bytes.

```text
URL_A != URL_B AND H_A = H_B
-> ONE_RAW_OBJECT + TWO_OBSERVATIONS
```

## 8. Immutability evidence boundary

Write-if-absent behavior is necessary but not sufficient for V06 historical immutability.

Acquisition MUST preserve inspectable evidence of its no-overwrite behavior, such as session events or exclusive-create outcomes, when available. However, acquisition MUST NOT insert a post-manifest evidence reference into a manifest row.

The reason is temporal and cryptographic:

```text
H_manifest does not exist until manifest bytes are final.
V06 evidence must bind H_manifest.
Therefore V06 evidence selection must occur after manifest finalization.
```

Correct ordering:

```text
ACQUISITION_COMPLETE
-> CANONICAL_MANIFEST
-> H_manifest
-> STORAGE_SEAL_EVIDENCE
-> IMMUTABILITY_BINDING
-> OFFLINE_GATE1
```

The storage-seal phase may run in the acquisition/operator environment after the manifest is frozen, but:

```text
SEALING_PHASE != VERIFICATION_ROLE
SEALING_PHASE MAY NOT MUTATE MANIFEST_BYTES
```

The cycle-free binding is defined by `gate1/immutability/binding-spec.md`.

```text
CURRENT_SNAPSHOT_CORRECT != HISTORICAL_IMMUTABILITY_PROVEN
```

## 9. Failure handling

Any required acquisition failure halts the capture under fail-closed policy.

Minimum failure classes:

```text
HTTP_STATUS
DNS
TIMEOUT
TLS
TRANSPORT
REDIRECT_POLICY
OTHER
```

For SSA profile acquisition, failure events validate against:

```text
profiles/ssa/schemas/SSA_FETCH_FAILURE_v0.1.schema.json
```

A failure receipt is never admitted as successful corpus bytes or a manifest observation.

```text
FETCH_FAILURE != B_a
FETCH_FAILURE != MANIFEST_OBSERVATION
FETCH_FAILURE != GATE1_PASS
```

No zero-byte placeholder, cached replacement, previous capture, synthetic response, inferred body, or error envelope may replace a missing required observation.

## 10. Fail-closed state transition

If any required scoped observation fails:

```text
ACQUISITION_STATUS = HALT_FAIL_CLOSED
MANIFEST_COMPLETION = FALSE
GATE1_ELIGIBLE = FALSE
L2_PLUS_ENABLED = FALSE
L3_6_ENABLED = FALSE
BASE_ATTESTATION = PROHIBITED
```

Successful objects from an incomplete attempt may remain preserved as evidence of what occurred, but the attempt cannot be relabeled complete.

A later retry is a new acquisition event with a new append-only identity.

## 11. Manifest and seal handoff

Acquisition produces observations. `manifest-spec.md` defines canonical manifest serialization and completeness.

Acquisition MUST NOT invent a completed manifest after required failure.

Only a complete capture may enter the manifest/seal handoff:

```text
ACQUISITION_COMPLETE
  -> CANONICAL_MANIFEST
  -> H_manifest
  -> CONTENT-ADDRESSED STORAGE-SEAL EVIDENCE
  -> CONTENT-ADDRESSED IMMUTABILITY BINDING
  -> OFFLINE_GATE1

ACQUISITION_INCOMPLETE
  -> TYPED_FAILURE
  -> HALT
```

The manifest is frozen before seal evidence is created. Seal artifacts may reference `H_manifest`; the manifest never points back to them.

## 12. Verification independence

Gate 1 consumes already-materialized inputs only.

The verifier MUST NOT:

- perform network requests;
- refetch a source;
- repair missing bytes;
- recalculate acquisition timestamps from the live web;
- substitute current content for captured content;
- modify acquisition, manifest, seal, or binding artifacts.

Receipt invariant:

```text
verification_mode = OFFLINE_IMPORTED_CORPUS
network_used = false
```

`network_used=false` is runtime-enforced, not caller supplied.

## 13. Authority boundary

Acquisition establishes only what bytes were observed under the declared request boundary.

It does not establish institutional endorsement, legal authority, policy truth/status, publication time, effective time, intent, or causation.

```text
OBSERVED_BYTES != INSTITUTIONAL_TRUTH
ACQUIRER != SOURCE
COMMITTER != SOURCE
```

## 14. Promotion firewall

```text
ACQUISITION_COMPLETE != V06_PASS
V06_PASS != GATE1_PASS
ACQUISITION_COMPLETE != INDEPENDENT_GATE1_PASS
NO H_G1^PASS -> BASE_ATTESTATION_PROHIBITED
GATE1 != PASS -> L3.6_PROHIBITED
```

Promotion remains impossible until the independent offline verifier evaluates all declared inputs under V01-V08 and emits a valid PASS receipt whose exact canonical receipt bytes are externally hashed as `H_G1`.
