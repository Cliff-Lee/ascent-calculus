"""GUI-1 research-workbench adapter.

The GUI package deliberately contains no independent combinatorial semantics.
It converts results from the AC engine into JSON-safe view models for a thin UI.
"""

from .viewmodel import (
    parse_word,
    inspect_word,
    trace_gap_swap_repair,
    bounded_check,
    research_status,
    interface_contract,
)

__all__ = [
    "parse_word",
    "inspect_word",
    "trace_gap_swap_repair",
    "bounded_check",
    "research_status",
    "interface_contract",
]
