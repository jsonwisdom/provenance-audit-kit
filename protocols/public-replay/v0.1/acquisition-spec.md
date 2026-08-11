# PUBLIC_REPLAY_ACQUISITION_SPEC_v0.1

Status: FROZEN DRAFT  
Protocol: `PUBLIC_REPLAY_PROTOCOL_v0.1`

This specification defines the acquisition boundary for public-institution replay corpora. Acquisition observes and stores public response bytes. It does not verify Gate 1, derive knowledge state, adjudicate policy, or create institutional authority.

## 1. Role separation

```text
ACQUISITION_ROLE != VERIFICATION_ROLE
LOCAL_ACQUISITION != GITHUB_VERIFICATION
```

`LOCAL_ACQUISITION` means an acquisition execution role independent from the verifier. It does **not** require a particular device or physical location. A laptop, Cloud Shell, controlled VM, or other operator-controlled environment may perform acquisition if it satisfies this specification.

The same execution event MUST NOT both acquire a corpus and act as the independent Gate-1 verifier for that corpus.

GitHub Actions MAY verify already-imported corpus inputs offline. GitHub Actions MUST NOT be required to originate the bytes it verifies.

## 2. Allowed acquisition environment

An allowed acquisition environment MUST:

- have ordinary network access to the declared public source;
- use only public, unauthenticated source surfaces declared by the institution profile and scope;
- declare the acquisition client and version;
- send a non-empty, truthful project User-Agent identifier;
- declare a non-empty operator/project contact value;
- declare its request timeout;
- declare its maximum request rate;
- record redirect behavior and the final effective URL;
- preserve the exact response body bytes returned by the source;
- preserve observed response headers needed for replay/provenance;
- use write-if-absent semantics for content-addressed raw objects;
- halt rather than repair a required acquisition failure.

The acquisition environment MUST NOT:

- authenticate to private claimant/account surfaces;
- use session cookies or credentials to expand public scope;
- bypass an access-control, WAF, CAPTCHA, robots policy, rate limit, or source restriction;
- rotate proxies, spoof browser identity, or otherwise conceal the acquisition client to defeat source controls;
- synthesize, normalize, reconstruct, or substitute missing response bytes;
- treat cached/search-engine/third-party bytes as source bytes unless the declared scope explicitly identifies that third party as the source being audited.

```text
SOURCE_DENIES_REQUEST -> TYPED_FAILURE
SOURCE_DENIES_REQUEST != BYPASS_AUTHORIZATION
```

## 3. Institution profile obligations

Each institution profile MUST declare acquisition policy fields sufficient to reproduce the request boundary, including at minimum:

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

For `PUBLIC_REPLAY_PROTOCOL_v0.1`, successful acquisition requires the final effective response to satisfy the profile's declared success status. A redirect may be followed only when allowed by the profile; the redirect chain and final effective URL MUST be retained as acquisition evidence.

Profile values constrain acquisition. They do not grant permission, create legal authority, or override source controls.

## 4. Capture identity

Every acquisition execution MUST create a new immutable `capture_id` before the first request.

A capture root is logically:

```text
capture/<capture_id>/
  raw/
  headers/
  receipts/
    fetch/
    failures/
  session/
```

The institution corpus layout MAY map these logical classes into the directory contract's canonical paths, but artifact class semantics MUST remain unchanged.

Reusing an existing `capture_id` to replace prior bytes is prohibited.

```text
CAPTURE_CREATED -> APPEND_ONLY
CAPTURE_REWRITE -> PROHIBITED
```

## 5. Successful observation

For source observation `a`, let `B_a` be the exact response body bytes returned by the final effective public source response.

```text
H_a = SHA256(B_a)
path(B_a) = corpus/raw/<H_a>
SHA256(read(path(B_a))) = H_a
```

A successful acquisition MUST retain at minimum:

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

`captured_at` records the acquisition environment's observation time. It is not trusted institutional time and is not proof of publication or effective-policy time.

```text
T_capture != T_publication != T_effective
```

The response body MUST be stored byte-for-byte. Content decoding, HTML parsing, PDF text extraction, whitespace normalization, decompression into a different representation, or other transformations are separate DERIVED artifacts and MUST NOT replace `B_a`.

## 6. Response headers

Observed response headers MUST be retained separately from body bytes.

Header storage MUST NOT alter `H_a`, which identifies only the exact response body bytes unless a future protocol version explicitly defines a different evidence object.

If headers are stored as a serialized artifact, their serialization procedure MUST be declared and their bytes independently hashed.

Headers are provenance evidence; they are not silently merged into the body object.

## 7. Write-if-absent rule

Raw storage is content-addressed and immutable.

When `corpus/raw/<H_a>` does not exist:

```text
CREATE_EXCLUSIVE(B_a)
```

When `corpus/raw/<H_a>` already exists:

```text
read(existing) == B_a -> REUSE_OBJECT
read(existing) != B_a -> MUTATION_PROHIBITED / HALT
```

Two observations MAY reference the same `H_a`. Observation deduplication MUST NOT erase the fact that two acquisition events occurred.

```text
URL_A != URL_B AND H_A = H_B
-> ONE_RAW_OBJECT + TWO_OBSERVATION_RECEIPTS
```

## 8. Immutability evidence boundary

Write-if-absent behavior during acquisition is necessary but is not, by itself, sufficient for Gate-1 V06 to claim historical immutability.

An acquisition implementation MUST produce or reference immutable evidence of the no-overwrite boundary that a later verifier can inspect. Examples include a hash-bound session event log, immutable repository object/commit reference, append-only object-store event record, or another protocol-declared artifact.

```text
CURRENT_SNAPSHOT_CORRECT != HISTORICAL_IMMUTABILITY_PROVEN
```

Gate 1 may assign `V06 = PASS` only from declared `immutability_evidence_refs` sufficient under the verification specification.

## 9. Failure handling

Any required acquisition failure MUST halt the capture under the fail-closed policy.

Failure classes include, at minimum:

```text
HTTP_STATUS
DNS
TIMEOUT
TLS
TRANSPORT
REDIRECT_POLICY
OTHER
```

For an SSA-profile acquisition, the failure event MUST validate against:

```text
profiles/ssa/schemas/SSA_FETCH_FAILURE_v0.1.schema.json
```

A failure receipt is evidence that an acquisition attempt failed. It is never admitted as successful corpus bytes or a manifest observation.

```text
FETCH_FAILURE != B_a
FETCH_FAILURE != MANIFEST_OBSERVATION
FETCH_FAILURE != GATE1_PASS
```

No zero-byte placeholder, cached replacement, previous capture, synthetic response, inferred body, or error envelope may be substituted for the missing required observation.

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

Previously captured successful objects from the incomplete capture MAY remain preserved as evidence of what occurred, but the incomplete capture MUST NOT be relabeled as complete.

A later retry is a new acquisition event. It MUST use a new `capture_id` or another protocol-defined append-only continuation identity; it MUST NOT rewrite the failed capture.

## 11. Manifest handoff boundary

Acquisition produces observations. `manifest-spec.md` defines their canonical manifest serialization and completeness rules.

Acquisition MUST NOT invent a completed `manifest.jsonl` after a required observation fails.

Only a capture satisfying the declared scope-completeness rule may be handed to the offline Gate-1 verifier.

```text
ACQUISITION_COMPLETE
  -> CANONICAL_MANIFEST
  -> OFFLINE_GATE1

ACQUISITION_INCOMPLETE
  -> TYPED_FAILURE
  -> HALT
```

## 12. Verification independence

Gate 1 consumes already-captured inputs only.

The verifier MUST NOT:

- perform network requests;
- refetch a source;
- repair missing bytes;
- recalculate acquisition timestamps from the live web;
- substitute current content for captured content;
- modify acquisition artifacts.

The Gate-1 receipt MUST enforce:

```text
verification_mode = OFFLINE_IMPORTED_CORPUS
network_used = false
```

`network_used = false` is a runtime invariant to be enforced by the generic verifier implementation, not merely a claimed receipt field.

## 13. Authority boundary

Acquisition establishes only what bytes were observed under the declared request boundary.

It does not establish:

- institutional endorsement;
- legal permission beyond what independently exists;
- policy truth;
- operative policy status;
- publication time;
- effective time;
- intent;
- causation.

```text
OBSERVED_BYTES != INSTITUTIONAL_TRUTH
ACQUIRER != SOURCE
COMMITTER != SOURCE
```

## 14. Promotion firewall

```text
ACQUISITION_COMPLETE != GATE1_PASS
ACQUISITION_COMPLETE != INDEPENDENT_GATE1_PASS
NO H_G1^PASS -> BASE_ATTESTATION_PROHIBITED
GATE1 != PASS -> L3.6_PROHIBITED
```

Acquisition is complete only when the declared public scope has been captured without required-observation failure. Promotion remains impossible until the independent offline verifier evaluates the imported corpus under V01-V08 and emits a valid PASS receipt whose exact receipt bytes are hashed externally as `H_G1`.
