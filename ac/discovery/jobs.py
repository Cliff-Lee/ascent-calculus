"""Transactional local persistence for long-running research jobs."""

from __future__ import annotations

from dataclasses import dataclass
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import sqlite3
import time
import uuid

from ac.discovery.specification import SearchSpec


JOB_STATUSES = ("queued", "running", "paused", "interrupted", "completed", "failed", "cancelled")


def default_job_database() -> Path:
    """Return the per-user durable job database path used by the desktop app."""
    override = os.environ.get("ASCENT_ENGINE_DATA_DIR")
    if override:
        root = Path(override).expanduser()
    elif os.name == "nt":
        root = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "AscentEngine"
    elif __import__("sys").platform == "darwin":
        root = Path.home() / "Library" / "Application Support" / "AscentEngine"
    else:
        root = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / "ascent-engine"
    return root / "research-jobs.sqlite3"


def _json(value) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"job data must be finite JSON values: {exc}") from exc


def _object(encoded: str | None) -> dict:
    value = json.loads(encoded or "{}")
    if not isinstance(value, dict):
        raise ValueError("stored job state is not a JSON object")
    return value


@dataclass(frozen=True)
class ResearchJob:
    id: str
    handler: str
    spec_json: str
    options: dict
    status: str
    control: str
    checkpoint: dict
    progress: dict
    result: dict | None
    error: str | None
    created_at: float
    updated_at: float
    heartbeat_at: float | None
    worker_id: str | None

    @property
    def question(self):
        raw = json.loads(self.spec_json)
        if isinstance(raw, dict) and raw.get("format") == "ascent-machine-search-spec":
            return SearchSpec.from_dict(raw)
        from ac.discovery.conjecture_search import ConjectureSearchSpec, DISCOVERY_FORMAT
        if isinstance(raw, dict) and raw.get("format") == DISCOVERY_FORMAT:
            return ConjectureSearchSpec.from_dict(raw)
        from ac.discovery.transformation_search import TransformationSearchSpec, TRANSFORM_SEARCH_FORMAT
        if isinstance(raw, dict) and raw.get("format") == TRANSFORM_SEARCH_FORMAT:
            return TransformationSearchSpec.from_dict(raw)
        from ac.discovery.transformation_family import TransformationFamilySearchSpec, FAMILY_SEARCH_FORMAT
        if isinstance(raw, dict) and raw.get("format") == FAMILY_SEARCH_FORMAT:
            return TransformationFamilySearchSpec.from_dict(raw)
        raise ValueError("stored research question has an unsupported format")

    @property
    def spec(self) -> SearchSpec:
        question = self.question
        if not isinstance(question, SearchSpec):
            raise ValueError("this research job uses a discovery plan, not a single SearchSpec")
        return question


class ResearchJobStore:
    """SQLite-backed, crash-safe job state and append-only transition log.

    Each state transition and checkpoint commits in one SQLite transaction.
    SQLite WAL plus FULL synchronous commits make the latest completed
    checkpoint durable before a worker begins its next unit of work.
    """

    def __init__(self, path: str | os.PathLike[str]):
        self.path = Path(path).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA synchronous=FULL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    handler TEXT NOT NULL,
                    spec_json TEXT NOT NULL,
                    options_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    control TEXT NOT NULL DEFAULT 'run',
                    checkpoint_json TEXT NOT NULL DEFAULT '{}',
                    progress_json TEXT NOT NULL DEFAULT '{}',
                    result_json TEXT,
                    error TEXT,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    heartbeat_at REAL,
                    worker_id TEXT
                );
                CREATE INDEX IF NOT EXISTS jobs_status_created ON jobs(status, created_at);
                CREATE TABLE IF NOT EXISTS job_events (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
                    event TEXT NOT NULL,
                    details_json TEXT NOT NULL,
                    created_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS job_ai_reviews (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
                    review_id TEXT NOT NULL,
                    review_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    UNIQUE(job_id, review_id)
                );
                CREATE INDEX IF NOT EXISTS job_ai_reviews_job
                    ON job_ai_reviews(job_id, seq);
                """
            )

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout=30000")
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA synchronous=FULL")
        try:
            yield connection
        finally:
            connection.close()

    @staticmethod
    def _event(connection, job_id: str, event: str, details: dict | None = None) -> None:
        connection.execute(
            "INSERT INTO job_events(job_id,event,details_json,created_at) VALUES(?,?,?,?)",
            (job_id, event, _json(details or {}), time.time()),
        )

    @staticmethod
    def _decode(row: sqlite3.Row | None) -> ResearchJob | None:
        if row is None:
            return None
        result = None if row["result_json"] is None else _object(row["result_json"])
        return ResearchJob(
            id=row["id"], handler=row["handler"], spec_json=row["spec_json"],
            options=_object(row["options_json"]), status=row["status"], control=row["control"],
            checkpoint=_object(row["checkpoint_json"]), progress=_object(row["progress_json"]),
            result=result, error=row["error"], created_at=row["created_at"],
            updated_at=row["updated_at"], heartbeat_at=row["heartbeat_at"], worker_id=row["worker_id"],
        )

    def create_job(
        self,
        spec: SearchSpec,
        *,
        handler: str,
        options: dict | None = None,
        job_id: str | None = None,
    ) -> ResearchJob:
        if not isinstance(spec, SearchSpec):
            from ac.discovery.conjecture_search import ConjectureSearchSpec
            from ac.discovery.transformation_search import TransformationSearchSpec
            from ac.discovery.transformation_family import TransformationFamilySearchSpec
            if not isinstance(spec, (ConjectureSearchSpec, TransformationSearchSpec, TransformationFamilySearchSpec)):
                raise ValueError("job requires a validated search specification")
        if not isinstance(handler, str) or re.fullmatch(r"[a-z][a-z0-9._-]{0,79}", handler) is None:
            raise ValueError("handler must be a registered lowercase job-handler id")
        options = {} if options is None else options
        if not isinstance(options, dict):
            raise ValueError("job options must be a JSON object")
        encoded_options = _json(options)
        identifier = job_id or uuid.uuid4().hex
        if not isinstance(identifier, str) or not identifier or len(identifier) > 128:
            raise ValueError("job id must be a nonempty string of at most 128 characters")
        now = time.time()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """INSERT INTO jobs(id,handler,spec_json,options_json,status,created_at,updated_at)
                   VALUES(?,?,?,?,?,?,?)""",
                (identifier, handler, spec.canonical_json(), encoded_options, "queued", now, now),
            )
            self._event(connection, identifier, "queued", {"handler": handler, "spec": spec.fingerprint})
            connection.commit()
        return self.get_job(identifier)

    def get_job(self, job_id: str) -> ResearchJob:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        job = self._decode(row)
        if job is None:
            raise KeyError(job_id)
        return job

    def list_jobs(self, *, statuses: tuple[str, ...] | None = None, limit: int = 100) -> tuple[ResearchJob, ...]:
        if type(limit) is not int or not 1 <= limit <= 10_000:
            raise ValueError("job list limit must be from 1 to 10000")
        with self._connect() as connection:
            if statuses:
                if any(status not in JOB_STATUSES for status in statuses):
                    raise ValueError("unknown job status")
                marks = ",".join("?" for _ in statuses)
                rows = connection.execute(
                    f"SELECT * FROM jobs WHERE status IN ({marks}) ORDER BY created_at,id LIMIT ?",
                    (*statuses, limit),
                ).fetchall()
            else:
                rows = connection.execute("SELECT * FROM jobs ORDER BY created_at DESC,id LIMIT ?", (limit,)).fetchall()
        return tuple(self._decode(row) for row in rows)

    def events(self, job_id: str, *, after: int = 0) -> tuple[dict, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT seq,event,details_json,created_at FROM job_events WHERE job_id=? AND seq>? ORDER BY seq",
                (job_id, after),
            ).fetchall()
        return tuple({"seq": row["seq"], "event": row["event"], "details": _object(row["details_json"]), "created_at": row["created_at"]} for row in rows)

    def record_assistant_review(self, job_id: str, review: dict) -> dict:
        """Persist one successful, unverified assistant exchange with a campaign."""
        from ac.ai.provenance import validate_assistant_review
        validate_assistant_review(review)
        encoded = _json(review)
        if len(encoded.encode("utf-8")) > 2_000_000:
            raise ValueError("assistant review exceeds the 2 MB per-review storage limit")
        review_id = review["review_id"]
        now = time.time()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if connection.execute("SELECT 1 FROM jobs WHERE id=?", (job_id,)).fetchone() is None:
                connection.rollback()
                raise KeyError(job_id)
            existing = connection.execute(
                "SELECT review_json FROM job_ai_reviews WHERE job_id=? AND review_id=?",
                (job_id, review_id),
            ).fetchone()
            if existing is not None:
                if existing["review_json"] != encoded:
                    connection.rollback()
                    raise ValueError("assistant review fingerprint already exists with different provenance")
                connection.commit()
                return json.loads(existing["review_json"])
            connection.execute(
                "INSERT INTO job_ai_reviews(job_id,review_id,review_json,created_at) VALUES(?,?,?,?)",
                (job_id, review_id, encoded, now),
            )
            self._event(connection, job_id, "assistant_review_saved", {
                "request_fingerprint": review_id,
                "provider_id": review["provider"]["id"],
                "model": review["request"]["model"],
            })
            connection.commit()
        return json.loads(encoded)

    def assistant_reviews(self, job_id: str) -> tuple[dict, ...]:
        """Return durable AI reviews in the order they were recorded."""
        with self._connect() as connection:
            if connection.execute("SELECT 1 FROM jobs WHERE id=?", (job_id,)).fetchone() is None:
                raise KeyError(job_id)
            rows = connection.execute(
                "SELECT review_json FROM job_ai_reviews WHERE job_id=? ORDER BY seq",
                (job_id,),
            ).fetchall()
        return tuple(json.loads(row["review_json"]) for row in rows)

    def claim_next(self, worker_id: str) -> ResearchJob | None:
        now = time.time()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT id FROM jobs WHERE status='queued' ORDER BY created_at,id LIMIT 1"
            ).fetchone()
            if row is None:
                connection.commit()
                return None
            identifier = row["id"]
            connection.execute(
                "UPDATE jobs SET status='running',control='run',worker_id=?,heartbeat_at=?,updated_at=? WHERE id=? AND status='queued'",
                (worker_id, now, now, identifier),
            )
            self._event(connection, identifier, "started", {"worker_id": worker_id})
            claimed = connection.execute("SELECT * FROM jobs WHERE id=?", (identifier,)).fetchone()
            connection.commit()
        return self._decode(claimed)

    def checkpoint(self, job_id: str, worker_id: str, checkpoint: dict, progress: dict) -> str:
        if not isinstance(checkpoint, dict) or not isinstance(progress, dict):
            raise ValueError("checkpoint and progress must be JSON objects")
        encoded_checkpoint, encoded_progress = _json(checkpoint), _json(progress)
        now = time.time()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT status,control,worker_id FROM jobs WHERE id=?", (job_id,)).fetchone()
            if row is None:
                raise KeyError(job_id)
            if row["status"] != "running" or row["worker_id"] != worker_id:
                connection.rollback()
                return row["status"]
            connection.execute(
                "UPDATE jobs SET checkpoint_json=?,progress_json=?,heartbeat_at=?,updated_at=? WHERE id=?",
                (encoded_checkpoint, encoded_progress, now, now, job_id),
            )
            connection.commit()
        return row["control"]

    def heartbeat(self, job_id: str, worker_id: str) -> bool:
        now = time.time()
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE jobs SET heartbeat_at=?,updated_at=? WHERE id=? AND status='running' AND worker_id=?",
                (now, now, job_id, worker_id),
            )
        return cursor.rowcount == 1

    def request_pause(self, job_id: str) -> ResearchJob:
        self._request_control(job_id, "pause")
        return self.get_job(job_id)

    def request_cancel(self, job_id: str) -> ResearchJob:
        self._request_control(job_id, "cancel")
        return self.get_job(job_id)

    def _request_control(self, job_id: str, control: str) -> None:
        now = time.time()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT status FROM jobs WHERE id=?", (job_id,)).fetchone()
            if row is None:
                raise KeyError(job_id)
            status = row["status"]
            if status == "queued":
                next_status = "paused" if control == "pause" else "cancelled"
                connection.execute("UPDATE jobs SET status=?,control=?,updated_at=? WHERE id=?", (next_status, control, now, job_id))
                self._event(connection, job_id, next_status, {})
            elif status == "running":
                connection.execute("UPDATE jobs SET control=?,updated_at=? WHERE id=?", (control, now, job_id))
                self._event(connection, job_id, control + "_requested", {})
            elif status in {"paused", "cancelled"}:
                connection.commit()
                return
            else:
                connection.rollback()
                raise ValueError(f"cannot request {control} for a {status} job")
            connection.commit()

    def finish(self, job_id: str, worker_id: str, result: dict) -> bool:
        encoded_result = _json(result)
        now = time.time()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT status,control,worker_id FROM jobs WHERE id=?", (job_id,)).fetchone()
            if row is None:
                raise KeyError(job_id)
            if row["status"] != "running" or row["worker_id"] != worker_id:
                connection.rollback()
                return False
            status = {"pause": "paused", "cancel": "cancelled"}.get(row["control"], "completed")
            connection.execute(
                "UPDATE jobs SET status=?,result_json=?,worker_id=NULL,heartbeat_at=NULL,updated_at=? WHERE id=?",
                (status, encoded_result, now, job_id),
            )
            self._event(connection, job_id, status, {})
            connection.commit()
        return True

    def stop_running(self, job_id: str, worker_id: str, *, status: str, error: str | None = None) -> None:
        if status not in {"paused", "cancelled", "failed"}:
            raise ValueError("worker stop status must be paused, cancelled, or failed")
        now = time.time()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                "UPDATE jobs SET status=?,worker_id=NULL,heartbeat_at=NULL,error=?,updated_at=? WHERE id=? AND status='running' AND worker_id=?",
                (status, error, now, job_id, worker_id),
            )
            if cursor.rowcount:
                self._event(connection, job_id, status, {"error": error} if error else {})
            connection.commit()

    def recover_stale_jobs(self, *, stale_after_seconds: float = 15.0) -> tuple[str, ...]:
        if isinstance(stale_after_seconds, bool) or not isinstance(stale_after_seconds, (int, float)) or stale_after_seconds < 0:
            raise ValueError("stale age must be a nonnegative number of seconds")
        cutoff = time.time() - float(stale_after_seconds)
        now = time.time()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute(
                "SELECT id FROM jobs WHERE status='running' AND COALESCE(heartbeat_at,updated_at)<=?",
                (cutoff,),
            ).fetchall()
            identifiers = tuple(row["id"] for row in rows)
            for identifier in identifiers:
                connection.execute(
                    "UPDATE jobs SET status='interrupted',control='run',worker_id=NULL,heartbeat_at=NULL,updated_at=? WHERE id=? AND status='running'",
                    (now, identifier),
                )
                self._event(connection, identifier, "interrupted", {"reason": "worker heartbeat expired"})
            connection.commit()
        return identifiers

    def resume_job(self, job_id: str) -> ResearchJob:
        now = time.time()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT status FROM jobs WHERE id=?", (job_id,)).fetchone()
            if row is None:
                raise KeyError(job_id)
            if row["status"] not in {"paused", "interrupted", "failed"}:
                connection.rollback()
                raise ValueError(f"cannot resume a {row['status']} job")
            connection.execute(
                "UPDATE jobs SET status='queued',control='run',worker_id=NULL,heartbeat_at=NULL,error=NULL,updated_at=? WHERE id=?",
                (now, job_id),
            )
            self._event(connection, job_id, "resumed", {})
            connection.commit()
        return self.get_job(job_id)

    def resume_all_interrupted(self) -> tuple[str, ...]:
        jobs = self.list_jobs(statuses=("interrupted",))
        return tuple(self.resume_job(job.id).id for job in jobs)

    def fail_queued(self, job_id: str, error: str) -> None:
        now = time.time()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                "UPDATE jobs SET status='failed',error=?,updated_at=? WHERE id=? AND status='queued'",
                (error[:100_000], now, job_id),
            )
            if cursor.rowcount:
                self._event(connection, job_id, "failed", {"error": error[:100_000]})
            connection.commit()

