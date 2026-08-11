# COMMIT INSTRUCTIONS — Steps 1-7 Exact Artifacts

MATERIALIZED_AT: 2026-08-11
PARENT: 51465bb9612c26b58897bc92404168c781b7af0f
BRANCH: feature/public-institution-replay-v0.1

Normative: 16/16 C01-C16 in constitution/fixtures/synthetic/ + _index.json
C11 = GATE1_AUTHORITY_BOUNDARY (frozen)
Supplemental: C17_EXTRA_FIXTURES_NOT_CREATE_RULES in constitution/fixtures/supplemental/ (NON_NORMATIVE)

Boundary lock:
- 16/16 != 17/17
- C17_EXTRA supplemental only

Files to commit:
- CONSTITUTION.md
- DIRECTORY_CONTRACT.md
- constitution/root.constitution.json
- constitution/directory-contract.schema.json
- constitution/DIRECTORY_CONTRACT.template.json
- constitution/DIRECTORY_CONTRACT.md
- constitution/fixtures/synthetic/*.json
- constitution/fixtures/supplemental/*.json
- audits/.../corpus/raw/DIRECTORY_CONTRACT.md
- audits/.../receipts/failures/DIRECTORY_CONTRACT.md
- COMMIT_INSTRUCTIONS.md (this file)

Commit message:
feat(constitution): materialize Genesis v0.1 Steps 1-7

C01-C16=FROZEN 16/16 C11=GATE1_AUTHORITY_BOUNDARY
C17_EXTRA=NON_NORMATIVE supplemental
MATERIALIZED_AT=2026-08-11
PARENT=51465bb9612c26b58897bc92404168c781b7af0f
AUTHORITY_CREATED=FALSE

Verification:
- SHA256 of tarball will be computed after push
- GitHub raw 200 for CONSTITUTION.md and _index.json
