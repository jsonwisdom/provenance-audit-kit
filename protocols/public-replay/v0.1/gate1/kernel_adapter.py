from __future__ import annotations

import hashlib
import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Callable


class KernelUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class ReceiptOSKernel:
    canonicalize_evidence: Callable[[Any], Any]
    canonical_json_receipt: Callable[[Any], str]
    evidence_canonicalizer_sha256: str
    receipt_json_sha256: str


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise KernelUnavailable(f"RECEIPTOS_KERNEL_IMPORT_FAILED path={path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        sys.modules.pop(name, None)
        raise KernelUnavailable(
            f"RECEIPTOS_KERNEL_IMPORT_FAILED path={path} error={type(exc).__name__}:{exc}"
        ) from exc
    return module


def load_receiptos_kernel(receiptos_root: Path) -> ReceiptOSKernel:
    root = receiptos_root.resolve()
    evidence_path = root / "ep" / "canonical.py"
    receipt_path = root / "receiptos" / "core" / "hash.py"

    for path in (evidence_path, receipt_path):
        if not path.is_file():
            raise KernelUnavailable(f"RECEIPTOS_KERNEL_MISSING path={path}")

    evidence_module = _load_module("public_replay_receiptos_ep_canonical", evidence_path)
    receipt_module = _load_module("public_replay_receiptos_core_hash", receipt_path)

    canonicalize = getattr(evidence_module, "canonicalize", None)
    canonical_json = getattr(receipt_module, "canonical_json", None)
    if not callable(canonicalize) or not callable(canonical_json):
        raise KernelUnavailable("RECEIPTOS_KERNEL_REQUIRED_CALLABLE_MISSING")

    return ReceiptOSKernel(
        canonicalize_evidence=canonicalize,
        canonical_json_receipt=canonical_json,
        evidence_canonicalizer_sha256=_sha256_file(evidence_path),
        receipt_json_sha256=_sha256_file(receipt_path),
    )
