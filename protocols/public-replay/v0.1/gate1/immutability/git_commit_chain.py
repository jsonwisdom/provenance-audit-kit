from __future__ import annotations

# Import first: the resolver inherits Gate 1's process-global offline guard.
import network_guard

import base64
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any

from kernel_adapter import ReceiptOSKernel


_EVIDENCE_REF = re.compile(r"^immutability/objects/([0-9a-f]{64})\.json$")
_PROOF_REF = re.compile(r"^immutability/proofs/([0-9a-f]{64})\.json$")
_ATTESTATION_REF = re.compile(r"^immutability/attestations/([0-9a-f]{64})\.json$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")

_EVIDENCE_FIELDS = {
    "schema",
    "capture_id",
    "H_manifest",
    "prev_H_manifest",
    "stored_at",
    "storage_id",
    "no_overwrite_attestation_ref",
    "repository",
    "object_format",
    "commit_id",
    "parent_commit_id",
    "tree_id",
    "manifest_path",
    "manifest_blob_id",
    "prev_manifest_blob_id",
    "proof_artifact_refs",
}
_PROOF_FIELDS = {"schema", "object_format", "object_type", "object_id", "content_b64"}
_ATTESTATION_FIELDS = {
    "schema",
    "mechanism",
    "object_format",
    "commit_id",
    "tree_id",
    "H_manifest",
    "invariant",
}


@dataclass(frozen=True)
class GitV06Result:
    V06: str
    reason: str
    evidence_H: str | None


@dataclass(frozen=True)
class _GitObject:
    object_type: str
    object_id: str
    content: bytes


class _ResolutionFailure(RuntimeError):
    def __init__(self, reason: str, message: str = "", evidence_H: str | None = None):
        super().__init__(message or reason)
        self.reason = reason
        self.evidence_H = evidence_H


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _oid_size(object_format: str) -> int:
    return 20 if object_format == "sha1" else 32


def _valid_oid(value: Any, object_format: str) -> bool:
    if not isinstance(value, str):
        return False
    expected = 40 if object_format == "sha1" else 64
    return len(value) == expected and re.fullmatch(r"[0-9a-f]+", value) is not None


def _git_oid(object_format: str, object_type: str, content: bytes) -> str:
    if object_format == "sha1":
        h = hashlib.sha1()
    elif object_format == "sha256":
        h = hashlib.sha256()
    else:
        raise _ResolutionFailure("IMMUTABILITY_EVIDENCE_SCHEMA_INVALID", "unsupported object format")
    h.update(f"{object_type} {len(content)}\0".encode("ascii"))
    h.update(content)
    return h.hexdigest()


def _safe_relative_path(value: Any) -> bool:
    if not isinstance(value, str) or not value or value.startswith("/"):
        return False
    p = PurePosixPath(value)
    return all(part not in {"", ".", ".."} for part in p.parts)


def _valid_rfc3339_utc(value: Any) -> bool:
    if not isinstance(value, str) or not value.endswith("Z"):
        return False
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return False
    return parsed.utcoffset() is not None and parsed.utcoffset().total_seconds() == 0


def _read_content_addressed_json(
    *,
    capture_root: Path,
    ref: str,
    pattern: re.Pattern[str],
    kernel: ReceiptOSKernel,
    invalid_reason: str,
    unresolved_reason: str,
    hash_reason: str,
    canonical_reason: str,
) -> tuple[dict[str, Any], str]:
    match = pattern.fullmatch(ref)
    if match is None:
        raise _ResolutionFailure(invalid_reason, f"invalid reference: {ref}")
    expected_h = match.group(1)
    root = capture_root.resolve()
    candidate = (root / PurePosixPath(ref)).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise _ResolutionFailure("IMMUTABILITY_PATH_TRAVERSAL", ref) from exc
    if not candidate.is_file():
        raise _ResolutionFailure(unresolved_reason, ref)
    data = candidate.read_bytes()
    actual_h = _sha256(data)
    if actual_h != expected_h:
        raise _ResolutionFailure(hash_reason, f"expected={expected_h} actual={actual_h}")
    if data.startswith(b"\xef\xbb\xbf"):
        raise _ResolutionFailure(canonical_reason, "UTF-8 BOM prohibited", expected_h)
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _ResolutionFailure(canonical_reason, type(exc).__name__, expected_h) from exc
    if not isinstance(value, dict):
        raise _ResolutionFailure(canonical_reason, "object required", expected_h)
    try:
        canonical = kernel.canonicalize_evidence(value).bytes + b"\n"
    except Exception as exc:
        raise _ResolutionFailure(canonical_reason, type(exc).__name__, expected_h) from exc
    if canonical != data:
        raise _ResolutionFailure(canonical_reason, "non-canonical bytes", expected_h)
    return value, expected_h


def _validate_evidence(value: dict[str, Any]) -> None:
    if set(value) != _EVIDENCE_FIELDS or value.get("schema") != "GIT_COMMIT_CHAIN_v0.1":
        raise _ResolutionFailure("IMMUTABILITY_EVIDENCE_SCHEMA_INVALID")
    object_format = value.get("object_format")
    if object_format not in {"sha1", "sha256"}:
        raise _ResolutionFailure("IMMUTABILITY_EVIDENCE_SCHEMA_INVALID")
    if not isinstance(value.get("capture_id"), str) or not value["capture_id"]:
        raise _ResolutionFailure("IMMUTABILITY_EVIDENCE_SCHEMA_INVALID")
    if not isinstance(value.get("repository"), str) or not value["repository"]:
        raise _ResolutionFailure("IMMUTABILITY_EVIDENCE_SCHEMA_INVALID")
    if _HEX64.fullmatch(str(value.get("H_manifest", ""))) is None:
        raise _ResolutionFailure("IMMUTABILITY_EVIDENCE_SCHEMA_INVALID")
    prev_h = value.get("prev_H_manifest")
    if prev_h is not None and (not isinstance(prev_h, str) or _HEX64.fullmatch(prev_h) is None):
        raise _ResolutionFailure("IMMUTABILITY_EVIDENCE_SCHEMA_INVALID")
    if not _valid_rfc3339_utc(value.get("stored_at")):
        raise _ResolutionFailure("IMMUTABILITY_EVIDENCE_SCHEMA_INVALID")
    for field in ("storage_id", "commit_id", "tree_id", "manifest_blob_id"):
        if not _valid_oid(value.get(field), object_format):
            raise _ResolutionFailure("IMMUTABILITY_EVIDENCE_SCHEMA_INVALID")
    if value["storage_id"] != value["commit_id"]:
        raise _ResolutionFailure("IMMUTABILITY_STORAGE_IDENTITY_MISMATCH")
    parent = value.get("parent_commit_id")
    if parent is not None and not _valid_oid(parent, object_format):
        raise _ResolutionFailure("IMMUTABILITY_EVIDENCE_SCHEMA_INVALID")
    prev_blob = value.get("prev_manifest_blob_id")
    if prev_blob is not None and not _valid_oid(prev_blob, object_format):
        raise _ResolutionFailure("IMMUTABILITY_EVIDENCE_SCHEMA_INVALID")
    if prev_h is None and prev_blob is not None:
        raise _ResolutionFailure("IMMUTABILITY_PARENT_BINDING_MISMATCH")
    if prev_h is not None and (parent is None or prev_blob is None):
        raise _ResolutionFailure("IMMUTABILITY_PARENT_BINDING_MISMATCH")
    if not _safe_relative_path(value.get("manifest_path")):
        raise _ResolutionFailure("IMMUTABILITY_EVIDENCE_SCHEMA_INVALID")
    if _ATTESTATION_REF.fullmatch(str(value.get("no_overwrite_attestation_ref", ""))) is None:
        raise _ResolutionFailure("IMMUTABILITY_EVIDENCE_SCHEMA_INVALID")
    refs = value.get("proof_artifact_refs")
    if not isinstance(refs, list) or len(refs) < 3 or len(refs) != len(set(refs)):
        raise _ResolutionFailure("IMMUTABILITY_EVIDENCE_SCHEMA_INVALID")
    if not all(isinstance(ref, str) and _PROOF_REF.fullmatch(ref) is not None for ref in refs):
        raise _ResolutionFailure("IMMUTABILITY_EVIDENCE_SCHEMA_INVALID")


def _validate_proof(value: dict[str, Any], expected_format: str) -> _GitObject:
    if set(value) != _PROOF_FIELDS or value.get("schema") != "GIT_OBJECT_PROOF_v0.1":
        raise _ResolutionFailure("IMMUTABILITY_EVIDENCE_SCHEMA_INVALID")
    if value.get("object_format") != expected_format:
        raise _ResolutionFailure("IMMUTABILITY_STORAGE_IDENTITY_MISMATCH")
    object_type = value.get("object_type")
    if object_type not in {"commit", "tree", "blob"}:
        raise _ResolutionFailure("IMMUTABILITY_EVIDENCE_SCHEMA_INVALID")
    object_id = value.get("object_id")
    if not _valid_oid(object_id, expected_format):
        raise _ResolutionFailure("IMMUTABILITY_EVIDENCE_SCHEMA_INVALID")
    content_b64 = value.get("content_b64")
    if not isinstance(content_b64, str):
        raise _ResolutionFailure("IMMUTABILITY_EVIDENCE_SCHEMA_INVALID")
    try:
        content = base64.b64decode(content_b64.encode("ascii"), validate=True)
    except Exception as exc:
        raise _ResolutionFailure("IMMUTABILITY_EVIDENCE_SCHEMA_INVALID", "invalid base64") from exc
    actual_id = _git_oid(expected_format, object_type, content)
    if actual_id != object_id:
        raise _ResolutionFailure(
            "IMMUTABILITY_STORAGE_IDENTITY_MISMATCH",
            f"git object mismatch expected={object_id} actual={actual_id}",
        )
    return _GitObject(object_type=object_type, object_id=object_id, content=content)


def _parse_commit(content: bytes, object_format: str) -> tuple[str, list[str]]:
    header = content.split(b"\n\n", 1)[0]
    tree_ids: list[str] = []
    parents: list[str] = []
    for line in header.split(b"\n"):
        if line.startswith(b"tree "):
            try:
                tree_ids.append(line[5:].decode("ascii"))
            except UnicodeDecodeError as exc:
                raise _ResolutionFailure("IMMUTABILITY_STORAGE_IDENTITY_MISMATCH") from exc
        elif line.startswith(b"parent "):
            try:
                parents.append(line[7:].decode("ascii"))
            except UnicodeDecodeError as exc:
                raise _ResolutionFailure("IMMUTABILITY_STORAGE_IDENTITY_MISMATCH") from exc
    if len(tree_ids) != 1 or not _valid_oid(tree_ids[0], object_format):
        raise _ResolutionFailure("IMMUTABILITY_STORAGE_IDENTITY_MISMATCH")
    if not all(_valid_oid(parent, object_format) for parent in parents):
        raise _ResolutionFailure("IMMUTABILITY_STORAGE_IDENTITY_MISMATCH")
    return tree_ids[0], parents


def _parse_tree(content: bytes, object_format: str) -> dict[bytes, tuple[bytes, str]]:
    oid_size = _oid_size(object_format)
    pos = 0
    result: dict[bytes, tuple[bytes, str]] = {}
    while pos < len(content):
        space = content.find(b" ", pos)
        if space < 0:
            raise _ResolutionFailure("IMMUTABILITY_STORAGE_IDENTITY_MISMATCH", "malformed tree mode")
        nul = content.find(b"\0", space + 1)
        if nul < 0:
            raise _ResolutionFailure("IMMUTABILITY_STORAGE_IDENTITY_MISMATCH", "malformed tree name")
        mode = content[pos:space]
        name = content[space + 1:nul]
        oid_start = nul + 1
        oid_end = oid_start + oid_size
        if oid_end > len(content) or not name or b"/" in name or name in {b".", b".."}:
            raise _ResolutionFailure("IMMUTABILITY_STORAGE_IDENTITY_MISMATCH", "malformed tree entry")
        oid = content[oid_start:oid_end].hex()
        if name in result:
            raise _ResolutionFailure("IMMUTABILITY_STORAGE_IDENTITY_MISMATCH", "duplicate tree entry")
        result[name] = (mode, oid)
        pos = oid_end
    return result


def _lookup_path(
    *,
    root_tree_id: str,
    path: str,
    objects: dict[str, _GitObject],
    object_format: str,
) -> str:
    if not _safe_relative_path(path):
        raise _ResolutionFailure("IMMUTABILITY_PATH_TRAVERSAL", path)
    segments = [part.encode("utf-8") for part in PurePosixPath(path).parts]
    current = root_tree_id
    for index, segment in enumerate(segments):
        tree = objects.get(current)
        if tree is None or tree.object_type != "tree":
            raise _ResolutionFailure("IMMUTABILITY_ATTESTATION_UNRESOLVABLE", f"tree={current}")
        entries = _parse_tree(tree.content, object_format)
        entry = entries.get(segment)
        if entry is None:
            raise _ResolutionFailure("IMMUTABILITY_STORAGE_IDENTITY_MISMATCH", path)
        _mode, child_id = entry
        if index == len(segments) - 1:
            return child_id
        child = objects.get(child_id)
        if child is None or child.object_type != "tree":
            raise _ResolutionFailure("IMMUTABILITY_ATTESTATION_UNRESOLVABLE", f"tree={child_id}")
        current = child_id
    raise _ResolutionFailure("IMMUTABILITY_STORAGE_IDENTITY_MISMATCH", path)


def _manifest_rows(manifest_bytes: bytes) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in manifest_bytes.splitlines():
        if not line:
            continue
        try:
            row = json.loads(line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise _ResolutionFailure("IMMUTABILITY_EVIDENCE_INSUFFICIENT", "manifest parse failed") from exc
        if not isinstance(row, dict):
            raise _ResolutionFailure("IMMUTABILITY_EVIDENCE_INSUFFICIENT", "manifest row not object")
        rows.append(row)
    if not rows:
        raise _ResolutionFailure("IMMUTABILITY_EVIDENCE_INSUFFICIENT", "empty manifest")
    return rows


def _validate_attestation(value: dict[str, Any], evidence: dict[str, Any]) -> None:
    if set(value) != _ATTESTATION_FIELDS:
        raise _ResolutionFailure("IMMUTABILITY_ATTESTATION_INVALID")
    expected = {
        "schema": "GIT_NO_OVERWRITE_ATTESTATION_v0.1",
        "mechanism": "GIT_CONTENT_ADDRESS_CHAIN",
        "object_format": evidence["object_format"],
        "commit_id": evidence["commit_id"],
        "tree_id": evidence["tree_id"],
        "H_manifest": evidence["H_manifest"],
        "invariant": "OBJECT_ID_EQUALS_HASH_OF_TYPED_CONTENT_AND_PARENT_OBJECTS_BIND_CHILD_IDENTITIES",
    }
    if value != expected:
        raise _ResolutionFailure("IMMUTABILITY_ATTESTATION_INVALID")


class GitCommitChainResolver:
    """Production implementation of GIT_COMMIT_CHAIN_v0.1.

    The class is implemented but is not wired into the production CLI until its
    real-ReceiptOS-kernel integration receipt is independently executed.
    """

    verifier_id = "GIT_COMMIT_CHAIN_RESOLVER_v0.1"

    def __init__(
        self,
        *,
        kernel: ReceiptOSKernel,
        manifest_path: Path,
        raw_root: Path,
    ) -> None:
        self.kernel = kernel
        self.manifest_path = manifest_path.resolve()
        self.raw_root = raw_root.resolve()
        if self.raw_root.name != "raw" or self.raw_root.parent.name != "corpus":
            raise ValueError("raw_root must be <capture_root>/corpus/raw")
        self.capture_root = self.raw_root.parent.parent.resolve()
        self.manifest_bytes = self.manifest_path.read_bytes()
        self.h_manifest = _sha256(self.manifest_bytes)
        self.rows = _manifest_rows(self.manifest_bytes)
        self._cache: dict[str, GitV06Result] = {}

    def resolve(self, evidence_ref: str) -> GitV06Result:
        if evidence_ref in self._cache:
            return self._cache[evidence_ref]
        evidence_h: str | None = None
        try:
            network_guard.assert_offline_invariant()
            if not isinstance(evidence_ref, str) or not evidence_ref:
                raise _ResolutionFailure("IMMUTABILITY_REF_MISSING")
            evidence, evidence_h = _read_content_addressed_json(
                capture_root=self.capture_root,
                ref=evidence_ref,
                pattern=_EVIDENCE_REF,
                kernel=self.kernel,
                invalid_reason="IMMUTABILITY_REF_INVALID",
                unresolved_reason="IMMUTABILITY_REF_UNRESOLVABLE",
                hash_reason="IMMUTABILITY_EVIDENCE_HASH_MISMATCH",
                canonical_reason="IMMUTABILITY_EVIDENCE_NOT_CANONICAL",
            )
            if evidence.get("schema") != "GIT_COMMIT_CHAIN_v0.1":
                raise _ResolutionFailure("IMMUTABILITY_EVIDENCE_TYPE_UNKNOWN", evidence_H=evidence_h)
            _validate_evidence(evidence)
            if evidence["H_manifest"] != self.h_manifest:
                raise _ResolutionFailure(
                    "IMMUTABILITY_MANIFEST_BINDING_MISMATCH", evidence_H=evidence_h
                )

            capture_ids = {row.get("capture_id") for row in self.rows}
            if capture_ids != {evidence["capture_id"]}:
                raise _ResolutionFailure(
                    "IMMUTABILITY_CAPTURE_BINDING_MISMATCH", evidence_H=evidence_h
                )

            objects: dict[str, _GitObject] = {}
            for proof_ref in evidence["proof_artifact_refs"]:
                proof, _proof_h = _read_content_addressed_json(
                    capture_root=self.capture_root,
                    ref=proof_ref,
                    pattern=_PROOF_REF,
                    kernel=self.kernel,
                    invalid_reason="IMMUTABILITY_REF_INVALID",
                    unresolved_reason="IMMUTABILITY_ATTESTATION_UNRESOLVABLE",
                    hash_reason="IMMUTABILITY_EVIDENCE_HASH_MISMATCH",
                    canonical_reason="IMMUTABILITY_EVIDENCE_NOT_CANONICAL",
                )
                obj = _validate_proof(proof, evidence["object_format"])
                existing = objects.get(obj.object_id)
                if existing is not None and existing != obj:
                    raise _ResolutionFailure(
                        "IMMUTABILITY_STORAGE_IDENTITY_MISMATCH", evidence_H=evidence_h
                    )
                objects[obj.object_id] = obj

            attestation, _att_h = _read_content_addressed_json(
                capture_root=self.capture_root,
                ref=evidence["no_overwrite_attestation_ref"],
                pattern=_ATTESTATION_REF,
                kernel=self.kernel,
                invalid_reason="IMMUTABILITY_REF_INVALID",
                unresolved_reason="IMMUTABILITY_ATTESTATION_UNRESOLVABLE",
                hash_reason="IMMUTABILITY_EVIDENCE_HASH_MISMATCH",
                canonical_reason="IMMUTABILITY_EVIDENCE_NOT_CANONICAL",
            )
            _validate_attestation(attestation, evidence)

            commit = objects.get(evidence["commit_id"])
            if commit is None or commit.object_type != "commit":
                raise _ResolutionFailure(
                    "IMMUTABILITY_ATTESTATION_UNRESOLVABLE", evidence_H=evidence_h
                )
            tree_id, parents = _parse_commit(commit.content, evidence["object_format"])
            if tree_id != evidence["tree_id"]:
                raise _ResolutionFailure(
                    "IMMUTABILITY_STORAGE_IDENTITY_MISMATCH", evidence_H=evidence_h
                )
            parent_commit_id = evidence["parent_commit_id"]
            if parent_commit_id is not None and parent_commit_id not in parents:
                raise _ResolutionFailure(
                    "IMMUTABILITY_PARENT_BINDING_MISMATCH", evidence_H=evidence_h
                )

            manifest_blob_id = _lookup_path(
                root_tree_id=evidence["tree_id"],
                path=evidence["manifest_path"],
                objects=objects,
                object_format=evidence["object_format"],
            )
            if manifest_blob_id != evidence["manifest_blob_id"]:
                raise _ResolutionFailure(
                    "IMMUTABILITY_STORAGE_IDENTITY_MISMATCH", evidence_H=evidence_h
                )
            manifest_blob = objects.get(manifest_blob_id)
            if manifest_blob is None or manifest_blob.object_type != "blob":
                raise _ResolutionFailure(
                    "IMMUTABILITY_ATTESTATION_UNRESOLVABLE", evidence_H=evidence_h
                )
            if manifest_blob.content != self.manifest_bytes:
                raise _ResolutionFailure(
                    "IMMUTABILITY_MANIFEST_BINDING_MISMATCH", evidence_H=evidence_h
                )

            for row in self.rows:
                digest = row.get("H_a")
                raw_ref = row.get("raw_ref")
                if not isinstance(digest, str) or _HEX64.fullmatch(digest) is None:
                    raise _ResolutionFailure(
                        "IMMUTABILITY_EVIDENCE_INSUFFICIENT", evidence_H=evidence_h
                    )
                if raw_ref != f"corpus/raw/{digest}" or not _safe_relative_path(raw_ref):
                    raise _ResolutionFailure(
                        "IMMUTABILITY_STORAGE_IDENTITY_MISMATCH", evidence_H=evidence_h
                    )
                raw_path = self.raw_root / digest
                if not raw_path.is_file():
                    raise _ResolutionFailure(
                        "IMMUTABILITY_ATTESTATION_UNRESOLVABLE", evidence_H=evidence_h
                    )
                raw_bytes = raw_path.read_bytes()
                if _sha256(raw_bytes) != digest:
                    raise _ResolutionFailure(
                        "IMMUTABILITY_STORAGE_IDENTITY_MISMATCH", evidence_H=evidence_h
                    )
                raw_blob_id = _lookup_path(
                    root_tree_id=evidence["tree_id"],
                    path=raw_ref,
                    objects=objects,
                    object_format=evidence["object_format"],
                )
                raw_blob = objects.get(raw_blob_id)
                if raw_blob is None or raw_blob.object_type != "blob":
                    raise _ResolutionFailure(
                        "IMMUTABILITY_ATTESTATION_UNRESOLVABLE", evidence_H=evidence_h
                    )
                if raw_blob.content != raw_bytes:
                    raise _ResolutionFailure(
                        "IMMUTABILITY_STORAGE_IDENTITY_MISMATCH", evidence_H=evidence_h
                    )

            prev_h = evidence["prev_H_manifest"]
            if prev_h is not None:
                parent_id = evidence["parent_commit_id"]
                parent_commit = objects.get(parent_id)
                if parent_commit is None or parent_commit.object_type != "commit":
                    raise _ResolutionFailure(
                        "IMMUTABILITY_ATTESTATION_UNRESOLVABLE", evidence_H=evidence_h
                    )
                parent_tree_id, _parent_parents = _parse_commit(
                    parent_commit.content, evidence["object_format"]
                )
                previous_blob_id = _lookup_path(
                    root_tree_id=parent_tree_id,
                    path=evidence["manifest_path"],
                    objects=objects,
                    object_format=evidence["object_format"],
                )
                if previous_blob_id != evidence["prev_manifest_blob_id"]:
                    raise _ResolutionFailure(
                        "IMMUTABILITY_PARENT_BINDING_MISMATCH", evidence_H=evidence_h
                    )
                previous_blob = objects.get(previous_blob_id)
                if previous_blob is None or previous_blob.object_type != "blob":
                    raise _ResolutionFailure(
                        "IMMUTABILITY_ATTESTATION_UNRESOLVABLE", evidence_H=evidence_h
                    )
                if _sha256(previous_blob.content) != prev_h:
                    raise _ResolutionFailure(
                        "IMMUTABILITY_PARENT_BINDING_MISMATCH", evidence_H=evidence_h
                    )

            network_guard.assert_offline_invariant()
            result = GitV06Result(
                V06="PASS",
                reason="IMMUTABILITY_VERIFIED",
                evidence_H=evidence_h,
            )
        except (network_guard.NetworkProhibited, network_guard.ProcessSpawnProhibited):
            result = GitV06Result(
                V06="FAIL",
                reason="IMMUTABILITY_RUNTIME_PROHIBITED_OPERATION",
                evidence_H=evidence_h,
            )
        except _ResolutionFailure as exc:
            result = GitV06Result(
                V06="FAIL",
                reason=exc.reason,
                evidence_H=exc.evidence_H if exc.evidence_H is not None else evidence_h,
            )
        except (OSError, ValueError, TypeError) as exc:
            result = GitV06Result(
                V06="FAIL",
                reason="IMMUTABILITY_EVIDENCE_INSUFFICIENT",
                evidence_H=evidence_h,
            )
        self._cache[evidence_ref] = result
        return result

    def verify(
        self,
        *,
        ref: str,
        row: dict[str, Any],
        capture_root: Path,
    ) -> tuple[bool, str]:
        if capture_root.resolve() != self.capture_root:
            return False, "IMMUTABILITY_CAPTURE_BINDING_MISMATCH"
        result = self.resolve(ref)
        if result.V06 != "PASS":
            return False, result.reason
        if row.get("capture_id") not in {r.get("capture_id") for r in self.rows}:
            return False, "IMMUTABILITY_CAPTURE_BINDING_MISMATCH"
        return True, result.reason
