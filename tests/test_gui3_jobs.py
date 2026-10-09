from threading import Event
from time import monotonic, sleep

import pytest

import ac.gui.jobs as jobs
from ac.gui.jobs import ExperimentJobManager, JobCapacityError


def _spec(stop=2):
    return {
        "question": "compare", "start": 1, "stop": stop,
        "left": {"family": "ordinary", "rules": []},
        "right": {"family": "ordinary", "rules": []},
    }


def _wait_for(manager, job_id, status, timeout=2):
    deadline = monotonic() + timeout
    while monotonic() < deadline:
        snapshot = manager.get(job_id)
        if snapshot["status"] == status:
            return snapshot
        sleep(0.01)
    raise AssertionError(f"Job {job_id} did not reach {status}: {manager.get(job_id)}")


def test_job_lifecycle_returns_progress_and_finite_result(monkeypatch):
    def fake_run(specification, *, progress, cancel_event):
        progress({"phase": "compare", "degree": 1, "completed_degrees": 0, "total_degrees": 1})
        return {"headline": "Match through n=1", "evidence": {"status": "verified", "finite_only": True}}

    monkeypatch.setattr(jobs, "run_experiment", fake_run)
    manager = ExperimentJobManager()

    started = manager.start("experiment", _spec(1))
    finished = _wait_for(manager, started["job_id"], "completed")

    assert finished["progress"]["phase"] == "compare"
    assert finished["result"]["evidence"]["finite_only"] is True
    assert "cancel_event" not in finished


def test_cancelled_job_finishes_as_cancelled_and_active_limit_is_enforced(monkeypatch):
    entered = Event()

    def wait_for_cancel(specification, *, progress, cancel_event):
        entered.set()
        progress({"phase": "compare", "degree": 4, "completed_degrees": 0, "total_degrees": 1})
        cancel_event.wait(2)
        return {"evidence": {"status": "incomplete", "finite_only": True}}

    monkeypatch.setattr(jobs, "run_experiment", wait_for_cancel)
    manager = ExperimentJobManager(max_active=1)
    started = manager.start("experiment", _spec(4))
    assert entered.wait(1)

    with pytest.raises(JobCapacityError):
        manager.start("experiment", _spec(1))

    assert manager.cancel(started["job_id"])["cancel_requested"] is True
    cancelled = _wait_for(manager, started["job_id"], "cancelled")
    assert cancelled["result"]["evidence"]["status"] == "incomplete"
    assert manager.cancel(started["job_id"])["cancel_requested"] is False


def test_job_manager_rejects_unknown_job_kind():
    with pytest.raises(ValueError, match="kind must be"):
        ExperimentJobManager().start("unknown", _spec())
