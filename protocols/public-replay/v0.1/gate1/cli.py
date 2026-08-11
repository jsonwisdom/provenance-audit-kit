#!/usr/bin/env python3
from __future__ import annotations

# Import first. This installs the offline socket/process guard before kernel/profile loading.
import network_guard

import argparse
import json
from pathlib import Path

from kernel_adapter import KernelUnavailable, load_receiptos_kernel
from verifier import Gate1InputError, verify_gate1


def main() -> int:
    parser = argparse.ArgumentParser(description="PUBLIC_REPLAY_GATE1_v0.1 offline verifier")
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--raw-root", required=True, type=Path)
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--receiptos-root", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    network_guard.assert_offline_invariant()
    kernel = load_receiptos_kernel(args.receiptos_root)
    result = verify_gate1(
        manifest_path=args.manifest,
        raw_root=args.raw_root,
        profile_path=args.profile,
        kernel=kernel,
    )
    network_guard.assert_offline_invariant()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    if args.out.exists():
        raise Gate1InputError(f"RECEIPT_OVERWRITE_PROHIBITED path={args.out}")
    args.out.write_bytes(result.receipt_bytes)

    sidecar = args.out.with_name(args.out.name + ".sha256")
    if sidecar.exists():
        raise Gate1InputError(f"SIDECAR_OVERWRITE_PROHIBITED path={sidecar}")
    sidecar.write_text(f"{result.h_g1}  {args.out.name}\n", encoding="ascii", newline="\n")

    print(json.dumps({
        "gate1_status": result.receipt["gate1_status"],
        "promotion_authorized": result.receipt["promotion_authorized"],
        "network_used": False,
        "H_manifest": result.receipt["manifest_sha256"],
        "H_G1": result.h_g1,
        "receipt": str(args.out),
        "receipt_sha256_sidecar": str(sidecar),
    }, sort_keys=True))
    return 0 if result.receipt["gate1_status"] == "PASS" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (
        Gate1InputError,
        KernelUnavailable,
        network_guard.NetworkProhibited,
        network_guard.ProcessSpawnProhibited,
        OSError,
        ValueError,
    ) as exc:
        print(json.dumps({
            "gate1_status": "FAIL_CLOSED_INPUT",
            "promotion_authorized": False,
            "network_used": False,
            "error": f"{type(exc).__name__}: {exc}",
        }, sort_keys=True))
        raise SystemExit(2)
