from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

from kernel_adapter import ReceiptOSKernel
from verifier import RejectUnresolvedImmutability, verify_gate1


class _CanonicalResult:
    def __init__(self, data: bytes):
        self.bytes = data


def _canonical_text(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _kernel():
    return ReceiptOSKernel(
        canonicalize_evidence=lambda value: _CanonicalResult(
            _canonical_text(value).encode("utf-8")
        ),
        canonical_json_receipt=_canonical_text,
        evidence_canonicalizer_sha256="a" * 64,
        receipt_json_sha256="b" * 64,
    )


class _PassImmutability:
    verifier_id = "TEST_IMMUTABILITY_PASS"

    def verify(self, *, ref, row, capture_root):
        return (ref == "immutability:test:1", "TEST_ONLY")


def _write_canonical(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_canonical_text(value).encode("utf-8") + b"\n")


class Gate1SurfaceTests(unittest.TestCase):
    def _fixture(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name) / "capture-001"
        raw_root = root / "corpus" / "raw"
        manifest = root / "manifests" / "manifest.jsonl"
        profile = root / "scope" / "profile.json"
        raw_root.mkdir(parents=True)

        body = b"public-source-bytes"
        digest = hashlib.sha256(body).hexdigest()
        raw_path = raw_root / digest
        raw_path.write_bytes(body)

        profile_value = {
            "allowed_urls": ["https://example.invalid/public"],
            "corpus_id": "TEST_CORPUS_v0.1",
            "profile_id": "TEST_PROFILE_v0.1",
            "protocol_id": "PUBLIC_REPLAY_PROTOCOL_v0.1",
            "receipt_schema": "TEST_GATE1_RECEIPT_v0.1",
            "required_urls": ["https://example.invalid/public"],
            "scope_id": "TEST_SCOPE_v0.1",
            "success_status_codes": [200],
        }
        _write_canonical(profile, profile_value)

        row = {
            "H_a": digest,
            "bytes_len": len(body),
            "capture_id": "capture-001",
            "corpus_admitted": True,
            "header_ref": "corpus/headers/header-001",
            "immutability_evidence_ref": "immutability:test:1",
            "mime_type": "text/plain",
            "observed_at": "2026-08-11T03:00:00Z",
            "profile_id": "TEST_PROFILE_v0.1",
            "raw_ref": f"corpus/raw/{digest}",
            "scope_id": "TEST_SCOPE_v0.1",
            "status_code": 200,
            "url": "https://example.invalid/public",
        }
        _write_canonical(manifest, row)
        return temp, manifest, raw_root, profile, raw_path

    def test_explicit_immutability_verifier_can_satisfy_v06(self):
        temp, manifest, raw_root, profile, _raw_path = self._fixture()
        try:
            result = verify_gate1(
                manifest_path=manifest,
                raw_root=raw_root,
                profile_path=profile,
                kernel=_kernel(),
                immutability_verifier=_PassImmutability(),
            )
            self.assertEqual(result.receipt["gate1_status"], "PASS")
            self.assertTrue(result.receipt["promotion_authorized"])
            self.assertEqual(
                result.receipt["check_results"],
                {f"V{i:02d}": "PASS" for i in range(1, 9)},
            )
            self.assertFalse(result.receipt["network_used"])
            self.assertNotIn("H_G1", result.receipt)
            self.assertEqual(
                hashlib.sha256(result.receipt_bytes).hexdigest(),
                result.h_g1,
            )
        finally:
            temp.cleanup()

    def test_default_immutability_resolver_fails_closed(self):
        temp, manifest, raw_root, profile, _raw_path = self._fixture()
        try:
            result = verify_gate1(
                manifest_path=manifest,
                raw_root=raw_root,
                profile_path=profile,
                kernel=_kernel(),
                immutability_verifier=RejectUnresolvedImmutability(),
            )
            self.assertEqual(result.receipt["check_results"]["V06"], "FAIL")
            self.assertEqual(result.receipt["check_results"]["V08"], "FAIL")
            self.assertEqual(result.receipt["gate1_status"], "FAIL")
            self.assertFalse(result.receipt["promotion_authorized"])
        finally:
            temp.cleanup()

    def test_missing_required_url_blocks_v07(self):
        temp, manifest, raw_root, profile, _raw_path = self._fixture()
        try:
            profile_value = json.loads(profile.read_text(encoding="utf-8"))
            missing_url = "https://example.invalid/required-but-missing"
            profile_value["allowed_urls"].append(missing_url)
            profile_value["required_urls"].append(missing_url)
            _write_canonical(profile, profile_value)

            result = verify_gate1(
                manifest_path=manifest,
                raw_root=raw_root,
                profile_path=profile,
                kernel=_kernel(),
                immutability_verifier=_PassImmutability(),
            )
            self.assertEqual(result.receipt["check_results"]["V07"], "FAIL")
            self.assertEqual(result.receipt["gate1_status"], "FAIL")
        finally:
            temp.cleanup()

    def test_missing_raw_object_counts_only_existing_objects(self):
        temp, manifest, raw_root, profile, raw_path = self._fixture()
        try:
            raw_path.unlink()
            result = verify_gate1(
                manifest_path=manifest,
                raw_root=raw_root,
                profile_path=profile,
                kernel=_kernel(),
                immutability_verifier=_PassImmutability(),
            )
            self.assertEqual(result.receipt["check_results"]["V02"], "FAIL")
            self.assertEqual(result.receipt["missing_objects"], 1)
            self.assertEqual(result.receipt["unique_raw_objects"], 0)
            self.assertEqual(result.receipt["duplicate_observations"], 0)
            self.assertEqual(result.receipt["gate1_status"], "FAIL")
        finally:
            temp.cleanup()


if __name__ == "__main__":
    unittest.main()
