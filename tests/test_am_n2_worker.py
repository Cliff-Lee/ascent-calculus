import tempfile
import time
from pathlib import Path

import pytest

from ac.discovery.jobs import ResearchJobStore
from ac.discovery.specification import ClassSpec, DegreeWindow, SearchSpec
from ac.discovery.worker import PersistentWorker, run_finite_search


def _wait_for(store, job_id, predicate, timeout=10):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        job = store.get_job(job_id)
        if predicate(job):
            return job
        time.sleep(0.01)
    raise AssertionError(f"timed out waiting for job {job_id}; state={store.get_job(job_id)}")


def test_worker_crash_recovers_from_the_last_committed_checkpoint():
    with tempfile.TemporaryDirectory() as directory:
        database = Path(directory) / "jobs.sqlite3"
        store = ResearchJobStore(database)
        spec = SearchSpec("enumerate", ClassSpec("ordinary"), DegreeWindow(1, 1))
        job = store.create_job(
            spec,
            handler="slow-counter",
            options={"steps": 14, "delay": 0.04},
        )

        handlers = {"slow-counter": "tests.worker_tasks:slow_checkpoint_counter"}
        first_worker = PersistentWorker(database, stale_after_seconds=0, idle_poll_seconds=0.02, handlers=handlers)
        first_worker.start()
        checkpointed = _wait_for(store, job.id, lambda item: item.checkpoint.get("cursor", 0) >= 1)
        first_worker.terminate_for_recovery_test()
        assert checkpointed.status == "running"

        assert store.recover_stale_jobs(stale_after_seconds=0) == (job.id,)
        interrupted = store.get_job(job.id)
        assert interrupted.status == "interrupted"
        saved_cursor = interrupted.checkpoint["cursor"]
        assert saved_cursor >= 1
        store.resume_job(job.id)

        second_worker = PersistentWorker(database, stale_after_seconds=0, idle_poll_seconds=0.02, handlers=handlers)
        try:
            second_worker.start()
            completed = _wait_for(store, job.id, lambda item: item.status == "completed")
            assert completed.result == {"steps": 14}
            assert completed.progress["steps_completed"] == 14
            names = [event["event"] for event in store.events(job.id)]
            assert "interrupted" in names and "resumed" in names and "completed" in names
        finally:
            second_worker.stop()


def test_finite_search_worker_checkpoints_shifted_class_comparisons():
    source = ClassSpec.build("modified", [{"mode": "avoid", "pattern": "111"}])
    target = ClassSpec.build("revised", [{"mode": "avoid", "pattern": "111"}])
    spec = SearchSpec(
        "count_equivalence", source, DegreeWindow(1, 4), target,
        target_offset=2, statistic="ascents",
    )
    fake_job = type("Job", (), {
        "spec": spec,
        "checkpoint": {},
    })()

    class Context:
        def __init__(self):
            self.saved = []

        def checkpoint(self, state, progress):
            self.saved.append((state, progress))

    context = Context()
    result = run_finite_search(fake_job, context)
    assert result["status"] == "finite_computation"
    assert result["interpretation"] == "bounded computation only; no theorem is inferred"
    assert len(result["rows"]) == 4
    assert [row["source_count"] for row in result["rows"]] == [1, 2, 4, 10]
    assert [row["target_count"] for row in result["rows"]] == [1, 2, 4, 10]
    assert all(row["counts_equal"] for row in result["rows"])
    # Equal counts do not imply that the chosen statistic is preserved.
    assert all(not row["profiles_equal"] for row in result["rows"])
    assert len(context.saved) == 4
    assert context.saved[-1][0]["next_base_degree"] == 5


def test_job_data_requires_a_versioned_search_question_and_finite_json_options():
    with tempfile.TemporaryDirectory() as directory:
        store = ResearchJobStore(Path(directory) / "jobs.sqlite3")
        with pytest.raises(ValueError, match="validated search specification"):
            store.create_job({}, handler="slow-counter")
        spec = SearchSpec("enumerate", ClassSpec("ordinary"), DegreeWindow(1, 1))
        with pytest.raises(ValueError, match="finite JSON"):
            store.create_job(spec, handler="finite-search", options={"bad": float("nan")})
