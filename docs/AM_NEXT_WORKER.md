# AM-Next N2 — Persistent jobs and checkpoints

N2 adds a local durable queue in `ac/discovery/jobs.py` and a separate worker
process in `ac/discovery/worker.py`. The database path defaults to the same
per-user data directory as saved desktop experiments and can be overridden
with `ASCENT_ENGINE_DATA_DIR` or `--database`.

## Job lifecycle

Each job stores the canonical N1 specification, a registered handler id,
finite JSON options, checkpoint state, progress, result, timestamps, and an
append-only lifecycle event log. The states are `queued`, `running`, `paused`,
`interrupted`, `completed`, `failed`, and `cancelled`.

SQLite uses write-ahead logging and full synchronous commits. Updating the
checkpoint and progress is one transaction. A worker commits the current safe
boundary before it starts the next unit of work. The worker process also sends
a heartbeat once per second while an individual unit is running. A restarted
worker marks jobs interrupted after their heartbeat expires and, by default,
queues their saved checkpoints for resumption.

Pausing or cancelling a job records a request immediately. The handler sees it
at its next checkpoint and stops there. Abrupt process termination leaves the
last committed checkpoint intact. Resumption repeats at most the current
incomplete unit; it does not resume from arbitrary Python stack state.

Job records store a **registered handler id**, not an import path. The worker
maps that id to code included by the application at startup. This prevents a
modified job database from naming and importing arbitrary modules. The built-in
handler is `finite-search`; test or future application handlers can be supplied
through the worker constructor by trusted application code.

## Current built-in computation

`finite-search` runs `enumerate`, `count_equivalence`, and
`profile_equivalence` specs, streaming each class one word at a time and
committing a row after each base degree. It supports source and target offsets
and conjunctive pattern rules. The current generation limits are enforced.
Results say `finite_computation`; they never claim a proof.

The built-in handler does not yet search transformations. A
`bijection_search` job fails with an explicit message until the generated typed
candidate language and counterexample loop are implemented. N3-N9 add discovery
handlers and candidate search.

## Use from Python

```python
from ac.discovery.jobs import ResearchJobStore, default_job_database
from ac.discovery.specification import ClassSpec, DegreeWindow, SearchSpec

source = ClassSpec.build("modified", [{"mode": "avoid", "pattern": "111"}])
target = ClassSpec.build("revised", [{"mode": "avoid", "pattern": "111"}])
question = SearchSpec(
    "count_equivalence", source, DegreeWindow(1, 5), target,
    target_offset=2,
)
jobs = ResearchJobStore(default_job_database())
job = jobs.create_job(question, handler="finite-search")
print(job.id, job.status)
```

Then run `ac-research-worker`, or from a source checkout run
`python -m ac.discovery.worker`. The worker waits for new jobs until interrupted.
Use `ResearchJobStore.get_job(job_id)` to inspect progress and the final result,
and `events(job_id)` to review its state transitions. The desktop interface
does not expose this queue yet; that integration is scheduled for N10.

## N2 validation boundary

`tests/test_am_n2_worker.py` starts a real spawned worker process, waits for a
committed checkpoint, terminates the process, verifies stale-job recovery,
resumes the job in a new process, and checks the exact final value. It also
tests shifted class comparison checkpoints, the built-in finite result status,
and finite-JSON validation.

The N2 gate validates persistence and process recovery, not overnight search
quality, workload budgeting, package-manager behavior, or a polished job
dashboard. macOS/Windows packaged multiprocessing still needs platform testing.
