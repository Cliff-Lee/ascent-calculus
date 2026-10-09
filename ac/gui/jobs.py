"""In-process lifecycle for long-running bounded research experiments."""

from __future__ import annotations

from datetime import datetime, timezone
from threading import Event, Lock, Thread
from time import monotonic
from uuid import uuid4

from .experiments import parse_experiment, run_experiment
from .transform_experiments import _parse as parse_transform_experiment
from .transform_experiments import run_transform_experiment


class JobCapacityError(RuntimeError):
    """Raised when the local workbench already has its active run allowance."""


class ExperimentJobManager:
    """Run engine-backed experiments on worker threads and expose snapshots."""

    def __init__(self, *, max_active: int = 2, max_retained: int = 32):
        self.max_active = max_active
        self.max_retained = max_retained
        self._lock = Lock()
        self._jobs: dict[str, dict] = {}

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _prune(self) -> None:
        finished = sorted(
            (job for job in self._jobs.values() if job["status"] in {"completed", "cancelled", "failed"}),
            key=lambda job: job["created_monotonic"],
        )
        excess = max(0, len(self._jobs) - self.max_retained)
        for job in finished[:excess]:
            self._jobs.pop(job["job_id"], None)

    def start(self, kind: str, specification: dict) -> dict:
        if kind == "experiment":
            parse_experiment(specification)
            runner = run_experiment
        elif kind == "transformation":
            parse_transform_experiment(specification)
            runner = run_transform_experiment
        else:
            raise ValueError("Job kind must be experiment or transformation")

        with self._lock:
            self._prune()
            active = sum(job["status"] in {"queued", "running", "cancelling"} for job in self._jobs.values())
            if active >= self.max_active:
                raise JobCapacityError(f"The local workbench allows at most {self.max_active} active runs")
            job_id = uuid4().hex
            now = self._now()
            cancel_event = Event()
            self._jobs[job_id] = {
                "job_id": job_id,
                "kind": kind,
                "status": "queued",
                "progress": {"phase": "queued", "completed_degrees": 0, "total_degrees": None},
                "result": None,
                "error": None,
                "created_at": now,
                "updated_at": now,
                "created_monotonic": monotonic(),
                "cancel_event": cancel_event,
            }

        thread = Thread(
            target=self._run,
            args=(job_id, runner, specification, cancel_event),
            name=f"ac-experiment-{job_id[:8]}",
            daemon=True,
        )
        thread.start()
        return self.get(job_id)

    def _set(self, job_id: str, **changes) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job.update(changes)
            job["updated_at"] = self._now()

    def _run(self, job_id: str, runner, specification: dict, cancel_event: Event) -> None:
        self._set(job_id, status="running")

        def report(update: dict) -> None:
            self._set(job_id, progress=dict(update))

        try:
            result = runner(specification, progress=report, cancel_event=cancel_event)
            status = "cancelled" if result.get("evidence", {}).get("status") == "incomplete" else "completed"
            self._set(job_id, status=status, result=result)
        except Exception as exc:  # keep the worker alive and expose a reviewable failure
            self._set(job_id, status="failed", error={"type": type(exc).__name__, "detail": str(exc)})

    def get(self, job_id: str) -> dict:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise KeyError(job_id)
            return {
                key: value for key, value in job.items()
                if key not in {"cancel_event", "created_monotonic"}
            }

    def cancel(self, job_id: str) -> dict:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise KeyError(job_id)
            if job["status"] not in {"queued", "running", "cancelling"}:
                return {"job_id": job_id, "cancel_requested": False, "status": job["status"]}
            job["cancel_event"].set()
            job["status"] = "cancelling"
            job["updated_at"] = self._now()
            return {"job_id": job_id, "cancel_requested": True, "status": job["status"]}
