# Findings directory contract

PURPOSE: Store derived, source-bound audit findings.

MAY_CONTAIN: Finding JSON that references verified receipts, capture commits, byte lengths, and hashes.

MUST_NOT_CONTAIN: Raw response bodies, admitted corpus objects, manifests, Gate1 receipts, claims of global availability, claims of institutional intent, or execution authority.

ENTRY_PRECONDITIONS: Every observation must resolve to an existing repository object and every conclusion must state its evidentiary boundary.

AUTHORITY_NOT_CREATED: A finding creates no SSA, legal, policy, institutional, Gate1, or execution authority.
