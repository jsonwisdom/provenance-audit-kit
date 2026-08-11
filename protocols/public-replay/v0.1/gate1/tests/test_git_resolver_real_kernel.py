from __future__ import annotations

import base64
import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import network_guard
from immutability.git_commit_chain import GitCommitChainResolver
from kernel_adapter import load_receiptos_kernel
from verifier import verify_gate1


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git_oid(object_type: str, content: bytes) -> str:
    h = hashlib.sha1()
    h.update(f"{object_type} {len(content)}\0".encode("ascii"))
    h.update(content)
    return h.hexdigest()


def _tree(entries: list[tuple[bytes, bytes, str]]) -> bytes:
    payload = bytearray()
    for mode, name, oid in sorted(entries, key=lambda item: item[1]):
        payload.extend(mode + b" " + name + b"\0" + bytes.fromhex(oid))
    return bytes(payload)


class RealKernelGitResolverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        receiptos_root = os.environ.get("RECEIPTOS_ROOT")
        if not receiptos_root:
            raise RuntimeError("RECEIPTOS_ROOT must point to a local receiptos-base checkout")
        cls.receiptos_root = Path(receiptos_root).resolve()
        cls.kernel = load_receiptos_kernel(cls.receiptos_root)
        network_guard.assert_offline_invariant()

    def _canonical_bytes(self, value) -> bytes:
        return self.kernel.canonicalize_evidence(value).bytes + b"\n"

    def _write_canonical(self, path: Path, value) -> bytes:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = self._canonical_bytes(value)
        path.write_bytes(data)
        return data

    def _write_content_addressed_json(self, root: Path, directory: str, value) -> tuple[str, Path]:
        data = self._canonical_bytes(value)
        digest = _sha256(data)
        path = root / "immutability" / directory / f"{digest}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return f"immutability/{directory}/{digest}.json", path

    def _proof(self, root: Path, object_type: str, content: bytes) -> tuple[str, str]:
        oid = _git_oid(object_type, content)
        value = {
            "content_b64": base64.b64encode(content).decode("ascii"),
            "object_format": "sha1",
            "object_id": oid,
            "object_type": object_type,
            "schema": "GIT_OBJECT_PROOF_v0.1",
        }
        ref, _path = self._write_content_addressed_json(root, "proofs", value)
        return oid, ref

    def _fixture(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name) / "capture-002"
        raw_root = root / "corpus" / "raw"
        manifest_path = root / "manifests" / "manifest.jsonl"
        profile_path = root / "scope" / "profile.json"
        raw_root.mkdir(parents=True)

        current_body = b"current-public-source-bytes"
        current_h = _sha256(current_body)
        (raw_root / current_h).write_bytes(current_body)

        row = {
            "H_a": current_h,
            "bytes_len": len(current_body),
            "capture_id": "capture-002",
            "corpus_admitted": True,
            "header_ref": "corpus/headers/header-current",
            "mime_type": "text/plain",
            "observed_at": "2026-08-11T04:00:00Z",
            "profile_id": "TEST_PROFILE_v0.1",
            "raw_ref": f"corpus/raw/{current_h}",
            "scope_id": "TEST_SCOPE_v0.1",
            "status_code": 200,
            "url": "https://example.invalid/public",
        }
        manifest_bytes = self._write_canonical(manifest_path, row)
        h_manifest = _sha256(manifest_bytes)

        profile = {
            "allowed_urls": ["https://example.invalid/public"],
            "corpus_id": "TEST_CORPUS_v0.1",
            "profile_id": "TEST_PROFILE_v0.1",
            "protocol_id": "PUBLIC_REPLAY_PROTOCOL_v0.1",
            "receipt_schema": "TEST_GATE1_RECEIPT_v0.1",
            "required_urls": ["https://example.invalid/public"],
            "scope_id": "TEST_SCOPE_v0.1",
            "success_status_codes": [200],
        }
        self._write_canonical(profile_path, profile)

        previous_row = dict(row)
        previous_row["capture_id"] = "capture-001"
        previous_row["observed_at"] = "2026-08-11T03:00:00Z"
        previous_manifest_bytes = self._canonical_bytes(previous_row)
        prev_h_manifest = _sha256(previous_manifest_bytes)

        proof_refs: list[str] = []

        prev_manifest_blob_id, ref = self._proof(root, "blob", previous_manifest_bytes)
        proof_refs.append(ref)
        prev_manifests_tree = _tree([(b"100644", b"manifest.jsonl", prev_manifest_blob_id)])
        prev_manifests_tree_id, ref = self._proof(root, "tree", prev_manifests_tree)
        proof_refs.append(ref)
        prev_root_tree = _tree([(b"40000", b"manifests", prev_manifests_tree_id)])
        prev_root_tree_id, ref = self._proof(root, "tree", prev_root_tree)
        proof_refs.append(ref)
        prev_commit_content = (
            f"tree {prev_root_tree_id}\n"
            "author ReceiptOS <receiptos@example.invalid> 0 +0000\n"
            "committer ReceiptOS <receiptos@example.invalid> 0 +0000\n"
            "\nprevious seal\n"
        ).encode("utf-8")
        prev_commit_id, ref = self._proof(root, "commit", prev_commit_content)
        proof_refs.append(ref)

        current_manifest_blob_id, ref = self._proof(root, "blob", manifest_bytes)
        proof_refs.append(ref)
        current_raw_blob_id, ref = self._proof(root, "blob", current_body)
        proof_refs.append(ref)
        raw_tree = _tree([(b"100644", current_h.encode("ascii"), current_raw_blob_id)])
        raw_tree_id, ref = self._proof(root, "tree", raw_tree)
        proof_refs.append(ref)
        corpus_tree = _tree([(b"40000", b"raw", raw_tree_id)])
        corpus_tree_id, ref = self._proof(root, "tree", corpus_tree)
        proof_refs.append(ref)
        manifests_tree = _tree([(b"100644", b"manifest.jsonl", current_manifest_blob_id)])
        manifests_tree_id, ref = self._proof(root, "tree", manifests_tree)
        proof_refs.append(ref)
        root_tree = _tree([
            (b"40000", b"corpus", corpus_tree_id),
            (b"40000", b"manifests", manifests_tree_id),
        ])
        root_tree_id, ref = self._proof(root, "tree", root_tree)
        proof_refs.append(ref)
        commit_content = (
            f"tree {root_tree_id}\n"
            f"parent {prev_commit_id}\n"
            "author ReceiptOS <receiptos@example.invalid> 1 +0000\n"
            "committer ReceiptOS <receiptos@example.invalid> 1 +0000\n"
            "\ncurrent seal\n"
        ).encode("utf-8")
        commit_id, ref = self._proof(root, "commit", commit_content)
        proof_refs.append(ref)

        attestation = {
            "H_manifest": h_manifest,
            "commit_id": commit_id,
            "invariant": "OBJECT_ID_EQUALS_HASH_OF_TYPED_CONTENT_AND_PARENT_OBJECTS_BIND_CHILD_IDENTITIES",
            "mechanism": "GIT_CONTENT_ADDRESS_CHAIN",
            "object_format": "sha1",
            "schema": "GIT_NO_OVERWRITE_ATTESTATION_v0.1",
            "tree_id": root_tree_id,
        }
        attestation_ref, _attestation_path = self._write_content_addressed_json(root, "attestations", attestation)

        evidence = {
            "H_manifest": h_manifest,
            "capture_id": "capture-002",
            "commit_id": commit_id,
            "manifest_blob_id": current_manifest_blob_id,
            "manifest_path": "manifests/manifest.jsonl",
            "no_overwrite_attestation_ref": attestation_ref,
            "object_format": "sha1",
            "parent_commit_id": prev_commit_id,
            "prev_H_manifest": prev_h_manifest,
            "prev_manifest_blob_id": prev_manifest_blob_id,
            "proof_artifact_refs": sorted(proof_refs),
            "repository": "offline-test-repository",
            "schema": "GIT_COMMIT_CHAIN_v0.1",
            "storage_id": commit_id,
            "stored_at": "2026-08-11T04:00:01Z",
            "tree_id": root_tree_id,
        }
        evidence_ref, evidence_path = self._write_content_addressed_json(root, "objects", evidence)

        binding = {
            "H_manifest": h_manifest,
            "capture_id": "capture-002",
            "evidence_ref": evidence_ref,
            "schema": "PUBLIC_REPLAY_IMMUTABILITY_BINDING_v0.1",
        }
        binding_bytes = self._canonical_bytes(binding)
        h_binding = _sha256(binding_bytes)
        binding_path = root / "immutability" / "bindings" / f"{h_binding}.json"
        binding_path.parent.mkdir(parents=True, exist_ok=True)
        binding_path.write_bytes(binding_bytes)

        resolver = GitCommitChainResolver(
            kernel=self.kernel,
            manifest_path=manifest_path,
            raw_root=raw_root,
        )
        return {
            "temp": temp,
            "root": root,
            "manifest": manifest_path,
            "raw_root": raw_root,
            "profile": profile_path,
            "binding": binding_path,
            "evidence_ref": evidence_ref,
            "evidence_path": evidence_path,
            "resolver": resolver,
            "h_manifest": h_manifest,
        }

    def test_git_chain_resolver_passes_with_parent_manifest_binding(self):
        f = self._fixture()
        try:
            result = f["resolver"].resolve(f["evidence_ref"])
            self.assertEqual(result.V06, "PASS")
            self.assertEqual(result.reason, "IMMUTABILITY_VERIFIED")
            self.assertEqual(result.evidence_H, f["evidence_ref"].split("/")[-1][:-5])
            network_guard.assert_offline_invariant()
        finally:
            f["temp"].cleanup()

    def test_gate1_is_deterministic_with_real_kernel_and_git_resolver(self):
        f = self._fixture()
        try:
            kwargs = dict(
                manifest_path=f["manifest"],
                raw_root=f["raw_root"],
                profile_path=f["profile"],
                immutability_binding_path=f["binding"],
                kernel=self.kernel,
                immutability_verifier=f["resolver"],
            )
            first = verify_gate1(**kwargs)
            second = verify_gate1(**kwargs)
            self.assertEqual(first.receipt["gate1_status"], "PASS")
            self.assertEqual(first.receipt["check_results"], {f"V{i:02d}": "PASS" for i in range(1, 9)})
            self.assertEqual(first.receipt_bytes, second.receipt_bytes)
            self.assertEqual(first.h_g1, second.h_g1)
            self.assertEqual(first.receipt["manifest_sha256"], f["h_manifest"])
            self.assertEqual(first.receipt["immutability_resolver"]["resolver_id"], "GIT_COMMIT_CHAIN_RESOLVER_v0.1")
            self.assertEqual(first.receipt["immutability_resolver"]["implementation_sha256"], f["resolver"].implementation_sha256)
            self.assertEqual(
                first.receipt["receiptos_kernel"]["evidence_canonicalizer_sha256"],
                _sha256((self.receiptos_root / "ep" / "canonical.py").read_bytes()),
            )
            self.assertEqual(
                first.receipt["receiptos_kernel"]["receipt_json_sha256"],
                _sha256((self.receiptos_root / "receiptos" / "core" / "hash.py").read_bytes()),
            )
            self.assertNotIn("verified_at", first.receipt)
            network_guard.assert_offline_invariant()
        finally:
            f["temp"].cleanup()

    def test_tampered_evidence_file_fails_content_address(self):
        f = self._fixture()
        try:
            original = f["evidence_path"].read_bytes()
            f["evidence_path"].write_bytes(original + b" ")
            result = f["resolver"].resolve(f["evidence_ref"])
            self.assertEqual(result.V06, "FAIL")
            self.assertEqual(result.reason, "IMMUTABILITY_EVIDENCE_HASH_MISMATCH")
        finally:
            f["temp"].cleanup()


if __name__ == "__main__":
    unittest.main()
