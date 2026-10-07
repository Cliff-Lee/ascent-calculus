from __future__ import annotations

from enum import Enum


class EvaluationMode(str, Enum):
    """How selector-controlled transformations obtain their targets.

    SNAPSHOT
        Evaluate the selector once on the source object, then transform all
        selected targets relative to that source.  This is the default AC
        semantics for insertion/deletion and is fully implemented.

    SEQUENTIAL
        Evaluate once, then visit the snapshotted targets in a specified order,
        re-anchoring by persistent source IDs after each edit.  Reserved for the
        sweep engine; the semantic distinction is frozen now even though the
        generic executor comes later.

    DYNAMIC
        Re-evaluate the selector after every step.  This can create loops and
        therefore belongs to explicit iterate/fixed-point constructs later.
    """

    SNAPSHOT = "snapshot"
    SEQUENTIAL = "sequential"
    DYNAMIC = "dynamic"
