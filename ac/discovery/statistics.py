"""Named finite statistics shared by the engine, GUI, and search records."""

from __future__ import annotations

from ac.core.word import ChainWord


STATISTICS: dict[str, str] = {
    "none": "Overall count",
    "ascents": "Number of ascents",
    "ascent_runs": "Number of ascent runs",
    "run_start_positions": "Ascent-run start positions",
    "run_lengths": "Ascent-run lengths",
    "maximum": "Maximum value",
    "distinct_values": "Number of distinct values",
    "multiplicity_partition": "Multiplicity partition",
    "first_occurrence_positions": "First-occurrence positions",
    "last_occurrence_positions": "Last-occurrence positions",
}


def statistic_value(word: ChainWord, statistic: str):
    """Evaluate one named statistic using the canonical AC conventions.

    ``none`` is the count-only mode and has no per-object value.  Unknown names
    fail explicitly so a saved search cannot silently change meaning after a
    typo or registry mismatch.
    """
    if statistic not in STATISTICS:
        raise ValueError(f"unknown statistic: {statistic}")
    if statistic == "none":
        return None
    if statistic == "ascents":
        return word.ascent_count
    if statistic == "ascent_runs":
        return len(word.run_starts)
    if statistic == "run_start_positions":
        return tuple(sorted(word.run_starts))
    if statistic == "run_lengths":
        starts = sorted(word.run_starts)
        boundaries = starts[1:] + [len(word) + 1]
        return tuple(end - start for start, end in zip(starts, boundaries))
    if statistic == "maximum":
        return max(word.values, default=0)
    if statistic == "distinct_values":
        return len(word.first_positions)
    if statistic == "multiplicity_partition":
        return word.integer_partition
    if statistic == "first_occurrence_positions":
        return tuple(sorted(word.first_positions))
    if statistic == "last_occurrence_positions":
        return tuple(sorted(word.last_positions))
    raise AssertionError("statistic registry and evaluator disagree")
