"""Compact rich progress reporter — one line per logical source."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

from rich.console import Console, Group
from rich.live import Live
from rich.progress_bar import ProgressBar
from rich.text import Text

from enrichrag.knowledge_graph.progress import ProgressEvent, ProgressReporter

# Map internal step names → display row name
STEP_TO_ROW: dict[str, str] = {
    "download_ncbi": "NCBI gene_info",
    "decompress_ncbi": "NCBI gene_info",
    "download_string_links": "STRING links",
    "decompress_string_links": "STRING links",
    "download_string_aliases": "STRING aliases",
    "decompress_string_aliases": "STRING aliases",
    "download_kegg": "KEGG pathways",
    "download_pubtator": "PubTator relations",
    "decompress_pubtator": "PubTator relations",
    "download_reactome": "Reactome FI",
    "extract_reactome": "Reactome FI",
    "build_gene_map": "Gene map",
    "normalize_string": "Normalize STRING",
    "normalize_kegg": "Normalize KEGG",
    "normalize_pubtator": "Normalize PubTator",
    "normalize_reactome": "Normalize Reactome",
    "load_gene_map": "Load gene map",
    "load_string": "Load STRING",
    "load_kegg": "Load KEGG",
    "load_pubtator": "Load PubTator",
    "load_reactome": "Load Reactome",
    "load_analyze": "Optimize DB",
}

_SPINNER_FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
_NAME_WIDTH = 22
_BAR_WIDTH = 20


def _format_bytes(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    elif n < 1024 * 1024:
        return f"{n / 1024:.0f} KB"
    elif n < 1024 * 1024 * 1024:
        return f"{n / 1024 / 1024:.1f} MB"
    else:
        return f"{n / 1024 / 1024 / 1024:.2f} GB"


def _format_count(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n:,}"
    return str(n)


@dataclass
class _RowState:
    name: str
    status: str = "waiting"  # waiting | active | done
    message: str = ""
    current: int = 0
    total: int = 0
    unit: str = ""
    order: int = 0  # insertion order


class RichProgressReporter(ProgressReporter):
    """Compact one-line-per-source progress display."""

    def __init__(self, console: Console | None = None):
        self.console = console or Console()
        self._rows: dict[str, _RowState] = {}
        self._lock = threading.Lock()
        self._order_counter = 0
        self._live: Live | None = None
        self._frame = 0

    def __enter__(self):
        self._live = Live(
            "",
            console=self.console,
            refresh_per_second=8,
            transient=False,
        )
        self._live.start()
        return self

    def __exit__(self, *args):
        if self._live:
            self._live.update(self._render())
            self._live.stop()
            self._live = None

    def _get_row(self, step: str) -> _RowState:
        row_name = STEP_TO_ROW.get(step, step)
        if row_name not in self._rows:
            self._rows[row_name] = _RowState(
                name=row_name, order=self._order_counter,
            )
            self._order_counter += 1
        return self._rows[row_name]

    def report(self, event: ProgressEvent) -> None:
        with self._lock:
            row = self._get_row(event.step)

            if event.done:
                row.status = "done"
                row.message = event.message
                if event.total > 0:
                    row.current = event.total
                    row.total = event.total
            else:
                row.status = "active"
                row.message = event.message
                row.current = event.current
                row.total = event.total
                row.unit = event.unit

        if self._live:
            self._frame += 1
            self._live.update(self._render())

    def _render(self) -> Group:
        lines = []
        sorted_rows = sorted(self._rows.values(), key=lambda r: r.order)

        for row in sorted_rows:
            line = self._render_row(row)
            lines.append(line)

        return Group(*lines)

    def _render_row(self, row: _RowState) -> Text:
        text = Text()

        # Icon
        if row.status == "done":
            text.append("  ✓ ", style="bold green")
        elif row.status == "active":
            spinner = _SPINNER_FRAMES[self._frame % len(_SPINNER_FRAMES)]
            text.append(f"  {spinner} ", style="bold cyan")
        else:
            text.append("  - ", style="dim")

        # Name (fixed width)
        name = row.name.ljust(_NAME_WIDTH)
        if row.status == "done":
            text.append(name, style="green")
        elif row.status == "active":
            text.append(name, style="bold")
        else:
            text.append(name, style="dim")

        # Detail
        if row.status == "done":
            text.append(self._done_detail(row), style="green")
        elif row.status == "active":
            text.append(self._active_detail(row))
        else:
            text.append("waiting", style="dim")

        return text

    def _done_detail(self, row: _RowState) -> str:
        msg = row.message
        # Extract useful info from the message
        if "cached" in msg.lower() or "already exists" in msg.lower():
            return "cached"
        if row.total > 0 and row.unit == "bytes":
            return _format_bytes(row.total)
        if row.total > 0:
            return f"{_format_count(row.total)} {row.unit}"
        # Fall back to message, strip step prefix
        for prefix in STEP_TO_ROW.values():
            if msg.startswith(prefix + ":"):
                msg = msg[len(prefix) + 1:].strip()
                break
        return msg

    def _active_detail(self, row: _RowState) -> str:
        if row.total > 0:
            pct = row.current / row.total if row.total else 0
            filled = int(_BAR_WIDTH * pct)
            bar = "━" * filled + "╺" + "─" * (_BAR_WIDTH - filled - 1)
            if row.unit == "bytes":
                return f"{bar} {pct:3.0%}  {_format_bytes(row.current)}/{_format_bytes(row.total)}"
            else:
                return f"{bar} {_format_count(row.current)}/{_format_count(row.total)} {row.unit}"
        elif row.current > 0:
            return f"{_format_count(row.current)} {row.unit}"
        else:
            # Extract short message
            msg = row.message
            for prefix in STEP_TO_ROW.values():
                if msg.startswith(prefix + ":"):
                    msg = msg[len(prefix) + 1:].strip()
                    break
            return msg
