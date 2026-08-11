from __future__ import annotations

import hashlib
import json
import os
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import network_guard
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
        canonicalize_evidence=lambda value: _CanonicalResult(_canonical_text(value).encode("utf-8")),
        canonical_json_receipt=_canonical_text,
        evidence_canonicalizer_sha256="a" * 64,
        receipt_json_sha256="b" * 64,
    )


class _PassImmutability:
    verifier_id = "TEST_IMMUTABILITY_PASS"
    implementation_sha256 = "c" * 64

    def verify(self, *, ref, capture_id, h_manifest, capture_root):
        expected = "immutability/objects/" + "d" * 64 + ".json"
        ok = (
            ref == expected
            and capture_id == "capture-001"
            and len(h_manifest) == 64
            and capture_root.name == "capture-001"
        )
        return ok, "TEST_ONLY" if ok else "TEST_BINDING_MISMATCH"


def _write_canonical(path: Path, value) -> bytes:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = _canonical_text(value).encode("utf-8") + b"\n"
    path.write_bytes(data)
    return data


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
            "mime_type": "text/plain",
            "observed_at": "2026-08-11T03:00:00Z",
            "profile_id": "TEST_PROFILE_v0.1",
            "raw_ref": f"corpus/raw/{digest}",
            "scope_id": "TEST_SCOPE_v0.1",
            "status_code": 200,
            "url": "https://example.invalid/public",
        }
        manifest_bytes = _write_canonical(manifest, row)
        h_manifest = hashlib.sha256(manifest_bytes).hexdigest()

        evidence_ref = "immutability/objects/" + "d" * 64 + ".json"
        binding_value = {
            "H_manifest": h_manifest,
            "capture_id": "capture-001",
            "evidence_ref": evidence_ref,
            "schema": "PUBLIC_REPLAY_IMMUTABILITY_BINDING_v0.1",
        }
        binding_bytes = _canonical_text(binding_value).encode("utf-8") + b"\n"
        h_binding = hashlib.sha256(binding_bytes).hexdigest()
        binding = root / "immutability" / "bindings" / f"{h_binding}.json"
        binding.parent.mkdir(parents=True)
        binding.write_bytes(binding_bytes)

        return temp, manifest, raw_root, profile, binding, raw_path, manifest_bytes, h_manifest

    def test_cycle_free_binding_does_not_change_manifest_identity(self):
        temp, manifest, _raw_root, _profile, binding, _raw_path, before, h_before = self._fixture()
        try:
            self.assertNotIn(b"immutability_evidence_ref", before)
            self.assertTrue(binding.is_file())
            after = manifest.read_bytes()
            self.assertEqual(before, after)
            self.assertEqual(h_before, hashlib.sha256(after).hexdigest())
        finally:
            temp.cleanup()

    def test_determinism_same_inputs_same_receipt_bytes_and_h_g1(self):
        temp, manifest, raw_root, profile, binding, _raw_path, _bytes, _h = self._fixture()
        try:
            kwargs = dict(
                manifest_path=manifest,
                raw_root=raw_root,
                profile_path=profile,
                immutability_binding_path=binding,
                kernel=_kernel(),
                immutability_verifier=_PassImmutability(),
            )
            first = verify_gate1(**kwargs)
            second = verify_gate1(**kwargs)
            self.assertEqual(first.receipt_bytes, second.receipt_bytes)
            self.assertEqual(first.h_g1, second.h_g1)
            self.assertNotIn("verified_at", first.receipt)
            self.assertNotIn("verified_at", second.receipt)
            self.assertEqual(first.receipt["verifier_sha256"], second.receipt["verifier_sha256"])
        finally:
            temp.cleanup()

    def test_explicit_immutability_verifier_can_satisfy_v06(self):
        temp, manifest, raw_root, profile, binding, _raw_path, _bytes, _h = self._fixture()
        try:
            result = verify_gate1(
                manifest_path=manifest,
                raw_root=raw_root,
                profile_path=profile,
                immutability_binding_path=binding,
                kernel=_kernel(),
                immutability_verifier=_PassImmutability(),
            )
            self.assertEqual(result.receipt["gate1_status"], "PASS")
            self.assertTrue(result.receipt["promotion_authorized"])
            self.assertEqual(result.receipt["check_results"], {f"V{i:02d}": "PASS" for i in range(1, 9)})
            self.assertFalse(result.receipt["network_used"])
            self.assertIsNotNone(result.receipt["immutability_binding_sha256"])
            self.assertEqual(result.receipt["immutability_resolver"]["implementation_sha256"], "c" * 64)
            self.assertNotIn("H_G1", result.receipt)
            self.assertEqual(hashlib.sha256(result.receipt_bytes).hexdigest(), result.h_g1)
        finally:
            temp.cleanup()

    def test_default_immutability_resolver_fails_closed(self):
        temp, manifest, raw_root, profile, binding, _raw_path, _bytes, _h = self._fixture()
        try:
            result = verify_gate1(
                manifest_path=manifest,
                raw_root=raw_root,
                profile_path=profile,
                immutability_binding_path=binding,
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
        temp, manifest, raw_root, profile, binding, _raw_path, _bytes, _h = self._fixture()
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
                immutability_binding_path=binding,
                kernel=_kernel(),
                immutability_verifier=_PassImmutability(),
            )
            self.assertEqual(result.receipt["check_results"]["V07"], "FAIL")
            self.assertEqual(result.receipt["gate1_status"], "FAIL")
        finally:
            temp.cleanup()

    def test_missing_raw_object_counts_only_existing_objects(self):
        temp, manifest, raw_root, profile, binding, raw_path, _bytes, _h = self._fixture()
        try:
            raw_path.unlink()
            result = verify_gate1(
                manifest_path=manifest,
                raw_root=raw_root,
                profile_path=profile,
                immutability_binding_path=binding,
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

    def test_binding_manifest_mismatch_blocks_v06(self):
        temp, manifest, raw_root, profile, binding, _raw_path, _bytes, _h = self._fixture()
        try:
            value = json.loads(binding.read_text(encoding="utf-8"))
            value["H_manifest"] = "0" * 64
            new_bytes = _canonical_text(value).encode("utf-8") + b"\n"
            new_h = hashlib.sha256(new_bytes).hexdigest()
            bad_binding = binding.parent / f"{new_h}.json"
            bad_binding.write_bytes(new_bytes)
            result = verify_gate1(
                manifest_path=manifest,
                raw_root=raw_root,
                profile_path=profile,
                immutability_binding_path=bad_binding,
                kernel=_kernel(),
                immutability_verifier=_PassImmutability(),
            )
            self.assertEqual(result.receipt["check_results"]["V06"], "FAIL")
            self.assertEqual(result.receipt["gate1_status"], "FAIL")
        finally:
            temp.cleanup()

    def test_zz_offline_guard_blocks_network_and_process_spawn(self):
        # This intentionally poisons process-global guard flags and therefore runs last.
        with self.assertRaises(network_guard.NetworkProhibited):
            socket.getaddrinfo("example.invalid", 443)
        with self.assertRaises(network_guard.NetworkProhibited):
            socket.socket()
        with self.assertRaises(network_guard.ProcessSpawnProhibited):
            subprocess.Popen(["true"])
        with self.assertRaises(network_guard.ProcessSpawnProhibited):
            os.system("true")
        self.assertTrue(network_guard.NETWORK_ATTEMPTED)
        self.assertTrue(network_guard.PROCESS_SPAWN_ATTEMPTED)
        self.assertFalse(network_guard.NETWORK_USED)


if __name__ == "__main__":
    unittest.main()
