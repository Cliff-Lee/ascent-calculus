"""Resumable process worker for bounded AC research jobs.

Handlers are importable ``module:function`` callables with signature
``handler(job, context) -> JSON object``. A handler checkpoints at safe points
before starting its next unit of work. Worker state and checkpoints live in
SQLite, so killing the worker does not corrupt the last committed boundary.
"""

from __future__ import annotations

from collections import Counter
import argparse
import importlib
import multiprocessing
import os
from pathlib import Path
import threading
import time
import traceback
from typing import Callable
import uuid

from ac.discovery.jobs import ResearchJob, ResearchJobStore, default_job_database
from ac.discovery.specification import SearchSpec
from ac.discovery.statistics import statistic_value


DEFAULT_HANDLERS = {
    "finite-search": "ac.discovery.worker:run_finite_search",
    "discover-pattern-classes": "ac.discovery.conjecture_search:run_worker_search",
    "analyze-structural-profiles": "ac.discovery.fingerprints:run_structural_profile_analysis",
    "search-transformations": "ac.discovery.transformation_search:run_transformation_search",
    "search-transformation-families": "ac.discovery.transformation_family:run_worker_search",
    "overnight-ai-transformation-campaign": "ac.discovery.overnight_campaign:run_overnight_campaign",
}


class PauseRequested(Exception):
    pass


class CancelRequested(Exception):
    pass


def _load_handler(path: str) -> Callable:
    module_name, function_name = path.split(":", 1)
    function = getattr(importlib.import_module(module_name), function_name, None)
    if not callable(function):
        raise ValueError(f"job handler is not callable: {path}")
    return function


class WorkerContext:
    def __init__(self, store: ResearchJobStore, job: ResearchJob, worker_id: str, stop_event):
        self.store = store
        self.job = job
        self.worker_id = worker_id
        self.stop_event = stop_event

    def checkpoint(self, state: dict, progress: dict | None = None) -> None:
        control = self.store.checkpoint(self.job.id, self.worker_id, state, progress or {})
        if self.stop_event.is_set() or control == "pause":
            raise PauseRequested
        if control == "cancel":
            raise CancelRequested
        if control != "run":
            raise PauseRequested

    def check_control(self) -> None:
        job = self.store.get_job(self.job.id)
        if job.status != "running" or job.worker_id != self.worker_id:
            raise PauseRequested
        if self.stop_event.is_set() or job.control == "pause":
            raise PauseRequested
        if job.control == "cancel":
            raise CancelRequested


def _heartbeat_loop(db_path: str, job_id: str, worker_id: str, done: threading.Event) -> None:
    store = ResearchJobStore(db_path)
    while not done.wait(1.0):
        if not store.heartbeat(job_id, worker_id):
            return


def _run_claimed_job(
    store: ResearchJobStore,
    job: ResearchJob,
    worker_id: str,
    stop_event,
    handlers: dict[str, str],
) -> None:
    heartbeat_done = threading.Event()
    heartbeat = threading.Thread(
        target=_heartbeat_loop,
        args=(str(store.path), job.id, worker_id, heartbeat_done),
        name=f"ac-heartbeat-{job.id[:8]}",
        daemon=True,
    )
    heartbeat.start()
    context = WorkerContext(store, job, worker_id, stop_event)
    try:
        handler_path = handlers.get(job.handler)
        if handler_path is None:
            raise ValueError(f"no worker handler is registered for id {job.handler!r}")
        handler = _load_handler(handler_path)
        context.check_control()
        result = handler(job, context)
        context.check_control()
        if not isinstance(result, dict):
            raise ValueError("job handler must return a JSON object")
        from ac.discovery.transformation_search import TransformationSearchSpec
        from ac.discovery.transformation_family import TransformationFamilySearchSpec
        question = job.question
        # Overnight campaigns store each finite search round against that
        # round's exact typed specification inside the handler. Recording the
        # aggregate report as though it answered the root question would
        # corrupt the research-memory lineage.
        if (
            job.handler != "overnight-ai-transformation-campaign"
            and isinstance(question, (TransformationSearchSpec, TransformationFamilySearchSpec))
        ):
            try:
                from ac.discovery.research_memory import ResearchMemoryStore
                memory_path = store.path.with_name("research-memory.sqlite3")
                memory_report = ResearchMemoryStore(memory_path).record_result(
                    question,
                    result,
                    run_id=job.id,
                    provenance={"handler": job.handler, "worker_id": worker_id},
                )
                result["research_memory"] = {"status": "recorded", **memory_report}
            except Exception as exc:
                # Preserve the completed mathematical result, while making a
                # memory-write problem visible in the durable job record.
                result["research_memory"] = {"status": "recording_failed", "detail": str(exc)}
        store.finish(job.id, worker_id, result)
    except PauseRequested:
        store.stop_running(job.id, worker_id, status="paused")
    except CancelRequested:
        store.stop_running(job.id, worker_id, status="cancelled")
    except BaseException:
        store.stop_running(job.id, worker_id, status="failed", error=traceback.format_exc()[-100_000:])
    finally:
        heartbeat_done.set()
        heartbeat.join(timeout=2)


def _worker_main(
    db_path: str,
    stop_event,
    idle_poll_seconds: float,
    stale_after_seconds: float,
    auto_resume_interrupted: bool,
    handlers: dict[str, str],
) -> None:
    store = ResearchJobStore(db_path)
    store.recover_stale_jobs(stale_after_seconds=stale_after_seconds)
    if auto_resume_interrupted:
        store.resume_all_interrupted()
    worker_id = f"{os.getpid()}-{uuid.uuid4().hex[:12]}"
    while not stop_event.is_set():
        job = store.claim_next(worker_id)
        if job is None:
            stop_event.wait(idle_poll_seconds)
            continue
        _run_claimed_job(store, job, worker_id, stop_event, handlers)


class PersistentWorker:
    """Parent-side lifecycle for one autonomous worker process.

    The child polls SQLite for queued jobs and keeps running until stopped.
    It can process jobs created by another UI process and resumes checkpointed
    jobs after stale workers are detected. Job records outlive this object.
    """

    def __init__(
        self,
        database: str | os.PathLike[str] | None = None,
        *,
        idle_poll_seconds: float = 0.25,
        stale_after_seconds: float = 15.0,
        auto_resume_interrupted: bool = True,
        handlers: dict[str, str] | None = None,
    ):
        if not 0.02 <= idle_poll_seconds <= 60:
            raise ValueError("worker idle poll interval must be between 0.02 and 60 seconds")
        if stale_after_seconds < 0:
            raise ValueError("stale worker age must be nonnegative")
        self.database = Path(database or default_job_database()).expanduser().resolve()
        ResearchJobStore(self.database)
        self.idle_poll_seconds = idle_poll_seconds
        self.stale_after_seconds = stale_after_seconds
        self.auto_resume_interrupted = auto_resume_interrupted
        self.handlers = dict(DEFAULT_HANDLERS if handlers is None else handlers)
        if any(
            not isinstance(key, str) or not key or not isinstance(path, str) or ":" not in path
            for key, path in self.handlers.items()
        ):
            raise ValueError("worker handlers must map registered ids to 'module:function' paths")
        self._context = multiprocessing.get_context("spawn")
        self._process = None
        self._stop_event = None

    @property
    def is_alive(self) -> bool:
        return self._process is not None and self._process.is_alive()

    @property
    def pid(self) -> int | None:
        return None if self._process is None else self._process.pid

    def start(self) -> int:
        if self.is_alive:
            return self._process.pid
        self._stop_event = self._context.Event()
        self._process = self._context.Process(
            target=_worker_main,
            args=(
                str(self.database), self._stop_event, self.idle_poll_seconds,
                self.stale_after_seconds, self.auto_resume_interrupted, self.handlers,
            ),
            name="ascent-machine-research-worker",
            daemon=True,
        )
        self._process.start()
        return self._process.pid

    def stop(self, *, timeout: float = 10.0) -> bool:
        """Request a checkpointed stop; return False if forced termination was needed."""
        if self._process is None or not self._process.is_alive():
            return True
        self._stop_event.set()
        self._process.join(timeout)
        if self._process.is_alive():
            self._process.terminate()
            self._process.join(5)
            return False
        return True

    def join(self, timeout: float | None = None) -> int | None:
        if self._process is None:
            return None
        self._process.join(timeout)
        return self._process.exitcode

    def terminate_for_recovery_test(self, *, timeout: float = 5.0) -> None:
        """Abruptly kill this process. Checkpoint recovery is handled by the store."""
        if self._process is not None and self._process.is_alive():
            self._process.terminate()
            self._process.join(timeout)


def _family_generator(family: str):
    if family == "ordinary":
        from ac.generate.universes import ascent_sequences
        return ascent_sequences
    if family == "modified":
        from ac.generate.universes import modified_via_hat
        return modified_via_hat
    if family == "revised":
        from ac.generate.universes import revised_sequences
        return revised_sequences
    raise ValueError(f"unsupported ascent-sequence family: {family}")


def _inspect_class(class_spec, degree: int, statistic: str | None):
    predicate = class_spec.predicate()
    count = 0
    distribution = Counter()
    for word in _family_generator(class_spec.family)(degree):
        if not predicate.holds(word):
            continue
        count += 1
        if statistic not in (None, "none"):
            distribution[statistic_value(word, statistic)] += 1
    return count, distribution


def _serial_profile(profile: Counter) -> list[dict]:
    return [
        {"value": value, "count": count}
        for value, count in sorted(profile.items(), key=lambda pair: repr(pair[0]))
    ]


def run_finite_search(job: ResearchJob, context: WorkerContext) -> dict:
    """Execute enumeration/count/profile questions one base degree at a time.

    Bijection synthesis is intentionally not dispatched here; it arrives with
    the generated typed grammar. Every degree row is committed before the
    worker starts the next degree, so resumption never depends on in-memory
    partial results.
    """
    from ac.gui.experiments import FAMILY_LIMITS

    spec = job.spec
    if spec.goal == "bijection_search":
        raise ValueError("the N2 worker handles enumeration and profile questions; transformation search is a later campaign stage")
    checkpoint = dict(job.checkpoint)
    rows = list(checkpoint.get("rows", []))
    completed = {row["base_degree"] for row in rows}
    next_base = checkpoint.get("next_base_degree", spec.degrees.start)
    if type(next_base) is not int:
        raise ValueError("job checkpoint has an invalid next base degree")

    for base_degree in range(max(spec.degrees.start, next_base), spec.degrees.stop + 1):
        source_degree, target_degree = spec.degrees_for(base_degree)
        sides = [("source", spec.source, source_degree)]
        if spec.target is not None:
            sides.append(("target", spec.target, target_degree))
        side_results: dict[str, tuple[int, Counter]] = {}
        for label, class_spec, degree in sides:
            if degree > FAMILY_LIMITS[class_spec.family]:
                raise ValueError(
                    f"{class_spec.family} generation is currently bounded to degree {FAMILY_LIMITS[class_spec.family]}"
                )
            side_results[label] = _inspect_class(class_spec, degree, spec.statistic)

        row = {
            "base_degree": base_degree,
            "source_degree": source_degree,
            "source_count": side_results["source"][0],
        }
        if spec.target is not None:
            row["target_degree"] = target_degree
            row["target_count"] = side_results["target"][0]
            row["counts_equal"] = row["source_count"] == row["target_count"]
        if spec.statistic not in (None, "none"):
            source_profile = side_results["source"][1]
            row["source_profile"] = _serial_profile(source_profile)
            if spec.target is not None:
                target_profile = side_results["target"][1]
                row["target_profile"] = _serial_profile(target_profile)
                row["profiles_equal"] = source_profile == target_profile
        rows = [existing for existing in rows if existing["base_degree"] != base_degree]
        rows.append(row)
        rows.sort(key=lambda existing: existing["base_degree"])
        completed.add(base_degree)
        context.checkpoint(
            {"next_base_degree": base_degree + 1, "rows": rows},
            {"completed_degrees": len(completed), "total_degrees": spec.degrees.stop - spec.degrees.start + 1,
             "current_base_degree": base_degree},
        )

    return {
        "spec_fingerprint": spec.fingerprint,
        "goal": spec.goal,
        "status": "finite_computation",
        "interpretation": "bounded computation only; no theorem is inferred",
        "rows": rows,
    }


def main(argv: list[str] | None = None) -> int:
    """Run the durable local queue until interrupted from the terminal."""
    parser = argparse.ArgumentParser(description="Run queued Ascent Machine research jobs")
    parser.add_argument("--database", type=Path, default=default_job_database(), help="SQLite job database")
    parser.add_argument("--poll", type=float, default=0.25, help="idle queue poll interval in seconds")
    parser.add_argument("--stale-after", type=float, default=15.0, help="seconds before an abandoned worker is recovered")
    parser.add_argument("--keep-interrupted", action="store_true", help="do not automatically resume interrupted jobs")
    args = parser.parse_args(argv)
    worker = PersistentWorker(
        args.database,
        idle_poll_seconds=args.poll,
        stale_after_seconds=args.stale_after,
        auto_resume_interrupted=not args.keep_interrupted,
    )
    pid = worker.start()
    print(f"Ascent Machine worker running (pid {pid}; database {worker.database})", flush=True)
    try:
        while worker.is_alive:
            worker.join(1)
    except KeyboardInterrupt:
        print("Stopping after the active checkpoint…", flush=True)
        worker.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

