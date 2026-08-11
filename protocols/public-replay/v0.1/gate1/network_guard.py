from __future__ import annotations

import socket
import sys
from typing import Any

NETWORK_USED = False
NETWORK_ATTEMPTED = False
_GUARD_INSTALLED = False


class NetworkProhibited(RuntimeError):
    pass


def _mark_and_fail(*args: Any, **kwargs: Any) -> Any:
    global NETWORK_ATTEMPTED
    NETWORK_ATTEMPTED = True
    raise NetworkProhibited("NETWORK_PROHIBITED: Gate 1 is offline-only")


def _audit_hook(event: str, args: tuple[Any, ...]) -> None:
    global NETWORK_ATTEMPTED
    if event in {
        "socket.__new__",
        "socket.connect",
        "socket.connect_ex",
        "socket.getaddrinfo",
        "socket.gethostbyname",
    }:
        NETWORK_ATTEMPTED = True
        raise NetworkProhibited(f"NETWORK_PROHIBITED audit_event={event}")


def install() -> None:
    global _GUARD_INSTALLED
    if _GUARD_INSTALLED:
        return
    sys.addaudithook(_audit_hook)
    socket.socket = _mark_and_fail  # type: ignore[assignment]
    socket.create_connection = _mark_and_fail  # type: ignore[assignment]
    socket.getaddrinfo = _mark_and_fail  # type: ignore[assignment]
    socket.gethostbyname = _mark_and_fail  # type: ignore[assignment]
    _GUARD_INSTALLED = True


def assert_offline_invariant() -> None:
    if not _GUARD_INSTALLED:
        raise RuntimeError("NETWORK_GUARD_NOT_INSTALLED")
    if NETWORK_USED:
        raise RuntimeError("NETWORK_USED_IN_OFFLINE_GATE1")
    if NETWORK_ATTEMPTED:
        raise RuntimeError("NETWORK_ATTEMPTED_IN_OFFLINE_GATE1")


install()
assert _GUARD_INSTALLED is True
assert NETWORK_USED is False
