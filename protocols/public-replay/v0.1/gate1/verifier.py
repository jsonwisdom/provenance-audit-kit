from __future__ import annotations

# Import first: any later socket/process attempt is a fail-closed execution violation.
import network_guard

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from kernel_adapter import ReceiptOSKernel

PROTOCOL_ID = "PUBLIC_REPLAY_PROTOCOL_v0.1"
VERIFIER_VERSION = "PUBLIC_REPLAY_GATE1_v0.1"
SERIALIZATION_PROFILE = "RECEIPTOS_NFC_JSON_V1_LF"
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
HEX64 = re.compile(r"^[0-9a-f]{64}$")
RFC3339_Z = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")

ROW_FIELDS = {
    "capture_id",
    "scope_id",
    "profile_id",
    "header_ref",
    "H_a",
    "bytes_len",
    "mime_type",
    "observed_at",
    "raw_ref",
    "status_code",
    "url",
    "corpus_admitted",
    "immutability_evidence_ref",
}


class Gate1InputError(RuntimeError):
    pass


class ImmutabilityVerifier(Protocol):
    verifier_id: str

    def verify(
        self,
        *,
        ref: str,
        row: dict[str, Any],
        capture_root: Path,
    ) -> tuple[bool, str]:
        ...


@dataclass(frozen=True)
class RejectUnresolvedImmutability:
    verifier_id: str = "UNRESOLVED_IMMUTABILITY_FAIL_CLOSED_v0.1"

    def verify(
        self,
        *,
        ref: str,
        row: dict[str, Any],
        capture_root: Path,
    ) -> tuple[bool, str]:
        return False, "UNRESOLVED_IMMUTABILITY_EVIDENCE"


@dataclass(frozen=True)
class Gate1Result:
    receipt: dict[str, Any]
    receipt_bytes: bytes
    h_g1: str


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_evidence_line(kernel: ReceiptOSKernel, value: Any) -> bytes:
    result = kernel.canonicalize_evidence(value)
    return result.bytes + b"\n"


def _load_profile(path: Path, kernel: ReceiptOSKernel) -> tuple[dict[str, Any], bytes]:
    data = path.read_bytes()
    if data.startswith(b"\xef\xbb\xbf"):
        raise Gate1InputError("PROFILE_UTF8_BOM_PROHIBITED")
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Gate1InputError(f"PROFILE_INVALID_JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise Gate1InputError("PROFILE_MUST_BE_OBJECT")

    try:
        canonical = _canonical_evidence_line(kernel, value)
    except Exception as exc:
        raise Gate1InputError(
            f"PROFILE_CANONICALIZATION_FAILED:{type(exc).__name__}"
        ) from exc
    if data != canonical:
        raise Gate1InputError("PROFILE_NOT_CANONICAL_BYTE_STRICT_JSONL")

    required = {
        "protocol_id",
        "profile_id",
        "scope_id",
        "corpus_id",
        "receipt_schema",
        "required_urls",
        "allowed_urls",
        "success_status_codes",
    }
    if set(value) != required:
        raise Gate1InputError("PROFILE_FIELDS_INVALID")
    if value["protocol_id"] != PROTOCOL_ID:
        raise Gate1InputError("PROFILE_PROTOCOL_MISMATCH")
    for field in ("profile_id", "scope_id", "corpus_id", "receipt_schema"):
        if not isinstance(value[field], str) or not value[field]:
            raise Gate1InputError(f"PROFILE_FIELD_INVALID:{field}")

    required_urls = value["required_urls"]
    allowed_urls = value["allowed_urls"]
    codes = value["success_status_codes"]
    if (
        not isinstance(required_urls, list)
        or not required_urls
        or len(set(required_urls)) != len(required_urls)
    ):
        raise Gate1InputError("PROFILE_REQUIRED_URLS_INVALID")
    if (
        not isinstance(allowed_urls, list)
        or not allowed_urls
        or len(set(allowed_urls)) != len(allowed_urls)
    ):
        raise Gate1InputError("PROFILE_ALLOWED_URLS_INVALID")
    if not all(
        isinstance(url, str) and url.startswith("https://")
        for url in required_urls + allowed_urls
    ):
        raise Gate1InputError("PROFILE_URL_INVALID")
    if not set(required_urls).issubset(set(allowed_urls)):
        raise Gate1InputError("PROFILE_REQUIRED_URL_NOT_ALLOWED")
    if not isinstance(codes, list) or not codes or len(set(codes)) != len(codes):
        raise Gate1InputError("PROFILE_STATUS_CODES_INVALID")
    if not all(
        isinstance(code, int)
        and not isinstance(code, bool)
        and 100 <= code <= 399
        for code in codes
    ):
        raise Gate1InputError("PROFILE_STATUS_CODE_INVALID")
    return value, data


def _error(
    errors: list[dict[str, Any]],
    check_id: str,
    code: str,
    message: str,
    row: int | None = None,
    ref: str | None = None,
) -> None:
    item: dict[str, Any] = {
        "check_id": check_id,
        "code": code,
        "message": message,
    }
    if row is not None:
        item["manifest_row"] = row
    if ref is not None:
        item["evidence_ref"] = ref
    errors.append(item)


def _valid_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or RFC3339_Z.fullmatch(value) is None:
        return False
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return False
    offset = parsed.utcoffset()
    return offset is not None and offset.total_seconds() == 0


def _validate_row_shape(row: Any) -> str | None:
    if not isinstance(row, dict):
        return "ROW_NOT_OBJECT"
    if set(row) != ROW_FIELDS:
        return "ROW_FIELDS_INVALID"
    for field in (
        "capture_id",
        "scope_id",
        "profile_id",
        "header_ref",
        "mime_type",
        "url",
    ):
        if not isinstance(row[field], str) or not row[field]:
            return f"ROW_FIELD_INVALID:{field}"
    if not isinstance(row["H_a"], str) or HEX64.fullmatch(row["H_a"]) is None:
        return "ROW_H_A_INVALID"
    if (
        not isinstance(row["bytes_len"], int)
        or isinstance(row["bytes_len"], bool)
        or row["bytes_len"] < 0
    ):
        return "ROW_BYTES_LEN_INVALID"
    if not isinstance(row["status_code"], int) or isinstance(row["status_code"], bool):
        return "ROW_STATUS_CODE_INVALID"
    if row["corpus_admitted"] is not True:
        return "ROW_NOT_CORPUS_ADMITTED"
    immutability_ref = row["immutability_evidence_ref"]
    if immutability_ref is not None and (
        not isinstance(immutability_ref, str) or not immutability_ref
    ):
        return "ROW_IMMUTABILITY_REF_INVALID"
    if not _valid_timestamp(row["observed_at"]):
        return "ROW_OBSERVED_AT_INVALID"
    if row["raw_ref"] != f"corpus/raw/{row['H_a']}":
        return "ROW_RAW_REF_NOT_CONTENT_ADDRESSED"
    return None


def _manifest_order_key(
    row: dict[str, Any],
) -> tuple[str, str, str, str, str, str]:
    return (
        row["url"],
        row["observed_at"],
        row["capture_id"],
        row["H_a"],
        row["raw_ref"],
        row["header_ref"],
    )


def verify_gate1(
    *,
    manifest_path: Path,
    raw_root: Path,
    profile_path: Path,
    kernel: ReceiptOSKernel,
    immutability_verifier: ImmutabilityVerifier | None = None,
) -> Gate1Result:
    network_guard.assert_offline_invariant()
    immutability_verifier = (
        immutability_verifier or RejectUnresolvedImmutability()
    )

    profile, profile_bytes = _load_profile(profile_path, kernel)
    manifest_bytes = manifest_path.read_bytes()
    h_manifest = _sha256(manifest_bytes)
    h_profile = _sha256(profile_bytes)

    errors: list[dict[str, Any]] = []
    checks = {f"V{i:02d}": "PASS" for i in range(1, 9)}
    rows: list[dict[str, Any]] = []
    canonical_rows: list[tuple[dict[str, Any], bytes, int]] = []
    line_count = 0
    malformed_rows = 0

    # V01: exact manifest canonicalization and row structure.
    if not manifest_bytes or h_manifest == EMPTY_SHA256:
        checks["V01"] = "FAIL"
        _error(errors, "V01", "EMPTY_MANIFEST", "manifest.jsonl must be non-empty")
    elif manifest_bytes.startswith(b"\xef\xbb\xbf"):
        checks["V01"] = "FAIL"
        _error(
            errors,
            "V01",
            "UTF8_BOM_PROHIBITED",
            "manifest.jsonl must not contain a UTF-8 BOM",
        )

    for index, line in enumerate(manifest_bytes.splitlines(keepends=True), 1):
        line_count += 1
        if not line.endswith(b"\n") or line.endswith(b"\r\n") or line == b"\n":
            malformed_rows += 1
            checks["V01"] = "FAIL"
            _error(
                errors,
                "V01",
                "NON_CANONICAL_LINE_ENDING",
                "Each manifest row must be non-blank and LF terminated",
                index,
            )
            continue

        payload = line[:-1]
        try:
            row = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            malformed_rows += 1
            checks["V01"] = "FAIL"
            _error(errors, "V01", "INVALID_JSON_ROW", str(exc), index)
            continue

        shape_error = _validate_row_shape(row)
        if shape_error:
            malformed_rows += 1
            checks["V01"] = "FAIL"
            _error(
                errors,
                "V01",
                shape_error,
                "Manifest row failed structural validation",
                index,
            )
            continue

        try:
            canonical_line = _canonical_evidence_line(kernel, row)
        except Exception as exc:
            malformed_rows += 1
            checks["V01"] = "FAIL"
            _error(
                errors,
                "V01",
                "CANONICALIZATION_FAILED",
                type(exc).__name__,
                index,
            )
            continue

        if line != canonical_line:
            malformed_rows += 1
            checks["V01"] = "FAIL"
            _error(
                errors,
                "V01",
                "ROW_NOT_CANONICAL",
                "Row bytes differ from ReceiptOS byte-strict canonical form",
                index,
            )

        canonical_rows.append((row, canonical_line, index))
        rows.append(row)

    if canonical_rows:
        expected_manifest = b"".join(
            item[1]
            for item in sorted(
                canonical_rows,
                key=lambda item: _manifest_order_key(item[0]),
            )
        )
        if expected_manifest != manifest_bytes:
            checks["V01"] = "FAIL"
            _error(
                errors,
                "V01",
                "MANIFEST_ORDER_OR_BYTES_NONCANONICAL",
                "Manifest bytes do not equal deterministically sorted canonical rows",
            )

    raw_root = raw_root.resolve()
    capture_root = raw_root.parent.parent
    if raw_root.name != "raw" or raw_root.parent.name != "corpus":
        checks["V05"] = "FAIL"
        _error(
            errors,
            "V05",
            "RAW_ROOT_LAYOUT_INVALID",
            "raw_root must be <capture_root>/corpus/raw",
        )

    missing_objects = 0
    hash_failures = 0
    length_failures = 0
    declared_hashes: set[str] = set()
    existing_hashes: set[str] = set()

    # V02-V04: existence, byte hash, exact length.
    for row, _line, index in canonical_rows:
        digest = row["H_a"]
        declared_hashes.add(digest)
        raw_path = raw_root / digest
        if not raw_path.is_file():
            missing_objects += 1
            checks["V02"] = "FAIL"
            _error(
                errors,
                "V02",
                "RAW_OBJECT_MISSING",
                f"Missing raw object {digest}",
                index,
            )
            continue

        existing_hashes.add(digest)
        data = raw_path.read_bytes()
        actual_hash = _sha256(data)
        if actual_hash != digest:
            hash_failures += 1
            checks["V03"] = "FAIL"
            _error(
                errors,
                "V03",
                "RAW_HASH_MISMATCH",
                f"expected={digest} actual={actual_hash}",
                index,
            )
        if len(data) != row["bytes_len"]:
            length_failures += 1
            checks["V04"] = "FAIL"
            _error(
                errors,
                "V04",
                "RAW_LENGTH_MISMATCH",
                f"expected={row['bytes_len']} actual={len(data)}",
                index,
            )

    # V05: one interpretation tuple, profile match, admitted-row constraints.
    tuples = {
        (row["capture_id"], row["scope_id"], row["profile_id"])
        for row in rows
    }
    expected_scope = profile["scope_id"]
    expected_profile = profile["profile_id"]
    allowed_urls = set(profile["allowed_urls"])
    success_codes = set(profile["success_status_codes"])

    if len(tuples) != 1:
        checks["V05"] = "FAIL"
        _error(
            errors,
            "V05",
            "MIXED_BINDING_TUPLE",
            "Manifest must contain exactly one capture_id/scope_id/profile_id tuple",
        )

    for row, _line, index in canonical_rows:
        if row["scope_id"] != expected_scope or row["profile_id"] != expected_profile:
            checks["V05"] = "FAIL"
            _error(
                errors,
                "V05",
                "PROFILE_SCOPE_BINDING_MISMATCH",
                "Manifest row does not match supplied profile/scope identity",
                index,
            )
        if row["url"] not in allowed_urls:
            checks["V05"] = "FAIL"
            _error(errors, "V05", "OUT_OF_SCOPE_URL", row["url"], index)
        if row["status_code"] not in success_codes:
            checks["V05"] = "FAIL"
            _error(
                errors,
                "V05",
                "STATUS_NOT_ADMITTED",
                str(row["status_code"]),
                index,
            )

    # V06: references are necessary but never sufficient without a resolver.
    immutability_refs: set[str] = set()
    if not rows:
        checks["V06"] = "FAIL"
        _error(
            errors,
            "V06",
            "NO_ROWS_FOR_IMMUTABILITY",
            "No admitted rows exist",
        )

    for row, _line, index in canonical_rows:
        ref = row["immutability_evidence_ref"]
        if ref is None:
            checks["V06"] = "FAIL"
            _error(
                errors,
                "V06",
                "IMMUTABILITY_REF_MISSING",
                "immutability_evidence_ref is null",
                index,
            )
            continue

        immutability_refs.add(ref)
        passed, reason = immutability_verifier.verify(
            ref=ref,
            row=row,
            capture_root=capture_root,
        )
        network_guard.assert_offline_invariant()
        if not passed:
            checks["V06"] = "FAIL"
            _error(
                errors,
                "V06",
                "IMMUTABILITY_EVIDENCE_INSUFFICIENT",
                reason,
                index,
                ref,
            )

    # V07: required-scope completion from the declared inputs only.
    # Typed acquisition failures cannot be admitted as manifest rows; a required
    # failed acquisition therefore leaves its required URL absent and V07 FAIL.
    required_urls = set(profile["required_urls"])
    observed_urls = {row["url"] for row in rows}
    missing_required = sorted(required_urls - observed_urls)
    if missing_required:
        checks["V07"] = "FAIL"
        _error(
            errors,
            "V07",
            "REQUIRED_SCOPE_INCOMPLETE",
            ",".join(missing_required),
        )

    # V08: deterministic promotion predicate only.
    pre_v08_errors = len(errors)
    v08_pass = (
        all(checks[f"V{i:02d}"] == "PASS" for i in range(1, 8))
        and line_count >= 1
        and len(existing_hashes) >= 1
        and missing_objects == 0
        and hash_failures == 0
        and length_failures == 0
        and malformed_rows == 0
        and pre_v08_errors == 0
    )
    checks["V08"] = "PASS" if v08_pass else "FAIL"
    if not v08_pass:
        _error(
            errors,
            "V08",
            "PROMOTION_PREDICATE_FAILED",
            "V01-V07 and zero-integrity-counter conjunction did not hold",
        )

    promotion_authorized = v08_pass
    receipt = {
        "schema": profile["receipt_schema"],
        "protocol_id": PROTOCOL_ID,
        "corpus_id": profile["corpus_id"],
        "scope_id": expected_scope,
        "profile_id": expected_profile,
        "profile_sha256": h_profile,
        "manifest_sha256": h_manifest,
        "manifest_rows_checked": line_count,
        "unique_raw_objects": len(existing_hashes),
        "duplicate_observations": max(0, len(rows) - len(declared_hashes)),
        "missing_objects": missing_objects,
        "hash_failures": hash_failures,
        "length_failures": length_failures,
        "malformed_rows": malformed_rows,
        "immutability_evidence_refs": sorted(immutability_refs),
        "check_results": checks,
        "errors": errors,
        "gate1_status": "PASS" if promotion_authorized else "FAIL",
        "promotion_authorized": promotion_authorized,
        "verification_mode": "OFFLINE_IMPORTED_CORPUS",
        "network_used": False,
        "serialization_profile": SERIALIZATION_PROFILE,
        "receiptos_kernel": {
            "repository": "jsonwisdom/receiptos-base",
            "evidence_canonicalizer_path": "ep/canonical.py",
            "evidence_canonicalizer_sha256": kernel.evidence_canonicalizer_sha256,
            "receipt_json_path": "receiptos/core/hash.py",
            "receipt_json_sha256": kernel.receipt_json_sha256,
        },
        "verifier_version": VERIFIER_VERSION,
    }

    network_guard.assert_offline_invariant()
    receipt_bytes = kernel.canonical_json_receipt(receipt).encode("utf-8") + b"\n"
    h_g1 = _sha256(receipt_bytes)
    return Gate1Result(receipt=receipt, receipt_bytes=receipt_bytes, h_g1=h_g1)
