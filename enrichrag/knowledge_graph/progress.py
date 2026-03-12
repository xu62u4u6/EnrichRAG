"""Progress reporting for KG build pipeline.

Provides a protocol-based abstraction so CLI (rich), web API (SSE),
and tests (silent) can all consume the same progress events.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class ProgressEvent:
    """A single progress update."""

    step: str  # e.g. "download_ncbi", "normalize_string", "load"
    message: str  # human-readable message
    current: int = 0  # current progress count
    total: int = 0  # total expected count (0 = indeterminate)
    unit: str = ""  # e.g. "bytes", "pathways", "edges", "entries"
    done: bool = False  # True when this step is complete


@runtime_checkable
class ProgressReporter(Protocol):
    """Interface for receiving progress events.

    Implementations:
    - RichProgressReporter: CLI with rich progress bars
    - SSEProgressReporter: Web API via server-sent events (future)
    - NullProgressReporter: Silent, for tests
    """

    def report(self, event: ProgressEvent) -> None: ...


class NullProgressReporter:
    """Silent progress reporter for tests and non-interactive use."""

    def report(self, event: ProgressEvent) -> None:
        pass


class CallbackProgressReporter:
    """Wraps a simple callback function as a ProgressReporter.

    Useful for bridging to existing callback-based code (e.g. pipeline.py).
    """

    def __init__(self, callback):
        self._callback = callback

    def report(self, event: ProgressEvent) -> None:
        self._callback(event)
