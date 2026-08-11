# PUBLIC_REPLAY_V06_RESOLVER_INTERFACE_v0.1

Status: FROZEN / GIT IMPLEMENTATION MATERIALIZED / REAL-KERNEL INTEGRATION PENDING

The production V06 resolver is an offline deterministic function over already-supplied artifacts.

## Generic result

A mechanism resolver exposes a deterministic result equivalent to:

```text
resolve(evidence_ref)
  -> { V06, reason, evidence_H }
```

Gate 1 supplies the manifest/raw context at resolver construction time and invokes a capture-level adapter:

```text
verify(
  ref,
  capture_id,
  h_manifest,
  capture_root
) -> (passed, reason)
```

For `GIT_COMMIT_CHAIN_v0.1`, the implementation is:

```text
GitCommitChainResolver(
  kernel,
  manifest_path,
  raw_root
)
```

The production CLI is NOT yet wired to that resolver. It remains fail-closed until an independent real-ReceiptOS-kernel integration receipt passes for the exact resolver/verifier head.

## Inputs

- `evidence_ref`: `immutability/objects/<evidence_H>.json`.
- exact canonical manifest bytes, recomputed by the resolver from `manifest_path`;
- exact content-addressed `raw_root`;
- exact `capture_id` and recomputed `H_manifest` supplied by Gate 1;
- content-addressed proof and attestation artifacts reachable only from the declared capture root.

The V06 evidence selection itself comes from the cycle-free post-manifest binding defined by `binding-spec.md`.

## Output

PASS:

```json
{
  "V06": "PASS",
  "reason": "IMMUTABILITY_VERIFIED",
  "evidence_H": "<64-lowercase-hex>"
}
```

FAIL:

```json
{
  "V06": "FAIL",
  "reason": "<TYPED_REASON>",
  "evidence_H": null
}
```

If a resolvable evidence object is identified but insufficient, `evidence_H` MAY be retained with `V06=FAIL`; identity does not imply sufficiency.

## Runtime prohibitions

```text
NETWORK_USED = FALSE
NETWORK_ATTEMPT = FAIL_CLOSED
CHILD_PROCESS = PROHIBITED
SHELL = PROHIBITED
REMOTE_LOOKUP = PROHIBITED
MUTATION = PROHIBITED
```

The resolver may read only declared local artifacts and may not write into the evidence/corpus input tree.

## Required checks

A conforming resolver MUST:

1. parse references without path traversal;
2. recompute `evidence_H` over exact canonical evidence bytes;
3. validate the registered evidence schema;
4. bind `capture_id` to the manifest tuple;
5. bind `H_manifest` to Gate-1's recomputed manifest hash;
6. verify `prev_H_manifest` chain semantics when present;
7. verify evidence-type-specific storage identities;
8. verify the no-overwrite assertion from offline evidence;
9. return FAIL on every unknown evidence type or unsupported algorithm;
10. expose a content identity for its own implementation so Gate-1 can bind resolver code into the receipt.

## Git-specific v0.1 requirements

`GIT_COMMIT_CHAIN_RESOLVER_v0.1` additionally MUST:

- recompute native Git commit/tree/blob IDs from exact object content without invoking `git`;
- ignore branch names as evidence;
- prove the current commit tree contains the exact `manifest.jsonl` bytes;
- prove the current commit tree contains every exact raw object named by the manifest;
- if `prev_H_manifest` is non-null, prove the selected parent commit contains the prior manifest bytes whose SHA-256 equals that value;
- verify the content-addressed Git no-overwrite attestation against the actual recomputed object chain.

## Typed FAIL vocabulary

Minimum reasons:

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

Unknown failures map to a stable fail-closed result.

## No authority escalation

```text
RESOLVER_PASS -> V06 PASS ONLY
V06 PASS -> DOES NOT BY ITSELF AUTHORIZE PROMOTION
```

The resolver cannot set Gate-1 status, `promotion_authorized`, L3.6 state, or witness state.

## Current production posture

```text
GIT_RESOLVER_IMPLEMENTED = TRUE
REAL_KERNEL_INTEGRATION_RECEIPT = MISSING
CLI_WIRED_TO_GIT_RESOLVER = FALSE
PRODUCTION_V06_PASS = PROHIBITED
PRODUCTION_GATE1_PASS = PROHIBITED
```
