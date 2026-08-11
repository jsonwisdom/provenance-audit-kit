# PUBLIC_REPLAY_V06_RESOLVER_INTERFACE_v0.1

Status: FROZEN DRAFT / IMPLEMENTATION_PROHIBITED_PENDING_TEST_EXECUTION

The production V06 resolver is an offline deterministic function over already-supplied artifacts.

```text
verify(evidence_ref, manifest, raw_root)
  -> { V06, reason, evidence_H }
```

## Inputs

- `evidence_ref`: content-addressed relative reference `immutability/objects/<evidence_H>.json`.
- `manifest`: exact canonical manifest bytes plus parsed rows.
- `raw_root`: exact content-addressed raw-object root already supplied to Gate 1.

The resolver may also receive read-only profile/configuration required to interpret a registered evidence type, but such configuration MUST be content-addressed and bound into the Gate-1 verification input domain before execution.

## Output

Exactly one deterministic result:

```json
{
  "V06": "PASS",
  "reason": "IMMUTABILITY_VERIFIED",
  "evidence_H": "<64-lowercase-hex>"
}
```

or:

```json
{
  "V06": "FAIL",
  "reason": "<TYPED_REASON>",
  "evidence_H": null
}
```

If the evidence file is resolvable and hashes correctly but is insufficient, `evidence_H` MAY be returned with `V06=FAIL`; callers must not interpret evidence identity as sufficiency.

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

A resolver MUST:

1. parse the reference without path traversal;
2. recompute `evidence_H` over exact canonical evidence bytes;
3. validate the registered evidence schema;
4. bind `capture_id` to the manifest tuple;
5. bind `H_manifest` to Gate-1's recomputed manifest hash;
6. verify `prev_H_manifest` semantics;
7. verify the evidence-type-specific storage identity;
8. verify the no-overwrite assertion using offline evidence;
9. return FAIL on every unknown evidence type or unsupported algorithm.

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

Unknown failures MUST map to a stable fail-closed reason rather than throwing an untyped success-adjacent state.

## No authority escalation

```text
RESOLVER_PASS -> V06 PASS ONLY
V06 PASS -> DOES NOT BY ITSELF AUTHORIZE PROMOTION
```

The resolver cannot set Gate-1 status, `promotion_authorized`, L3.6 state, or witness state.
