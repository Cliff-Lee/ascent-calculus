"""Small importable process-worker tasks used only by worker tests."""

from __future__ import annotations

import time


def slow_checkpoint_counter(job, context):
    cursor = int(job.checkpoint.get("cursor", 0))
    limit = int(job.options["steps"])
    delay = float(job.options.get("delay", 0.02))
    while cursor < limit:
        time.sleep(delay)
        cursor += 1
        context.checkpoint({"cursor": cursor}, {"steps_completed": cursor, "steps_total": limit})
    return {"steps": cursor}
