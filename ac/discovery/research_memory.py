"""Durable candidate memory, normal-form deduplication, and novelty reports."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time
import uuid
from contextlib import contextmanager


MEMORY_SCHEMA_VERSION = 1
MEMORY_ENGINE_VERSION = "am-next-research-memory-v1"


def default_research_memory_database() -> Path:
    override = os.environ.get("ASCENT_ENGINE_DATA_DIR")
    if override:
        root = Path(override).expanduser()
        return root / "research-memory.sqlite3"
    from ac.discovery.jobs import default_job_database
    return default_job_database().with_name("research-memory.sqlite3")


def _json(value) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"research-memory records must be finite JSON values: {exc}") from exc


def _hash(value) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _failure_signature(row: dict) -> dict | None:
    failure = row.get("first_failure") or row.get("counterexample")
    if failure is None:
        return None
    return {
        "kind": failure.get("kind"),
        "base_degree": failure.get("base_degree"),
        "source": failure.get("source"),
        "other_source": failure.get("other_source"),
        "output": failure.get("output"),
    }


def _behavior_signature(row: dict, question_fingerprint: str) -> tuple[str, bool]:
    scenarios = row.get("scenario_results")
    if isinstance(scenarios, list):
        behavior = [
            {
                "specification_fingerprint": scenario.get("specification_fingerprint"),
                "finite_match": bool(scenario.get("finite_match")),
                "verified_through": scenario.get("verified_through"),
                "finite_map_fingerprint": scenario.get("evaluation", {}).get("finite_map_fingerprint"),
                "failure": _failure_signature(scenario.get("evaluation", {})),
            }
            for scenario in scenarios
        ]
        finite_map = bool(scenarios) and all(
            scenario.get("finite_match")
            and scenario.get("evaluation", {}).get("finite_map_fingerprint")
            for scenario in scenarios
        )
    else:
        finite_map = bool(row.get("finite_match_through_window")) and bool(row.get("finite_map_fingerprint"))
        behavior = {
            "finite_match": bool(row.get("finite_match_through_window")),
            "verified_through": row.get("verified_through"),
            "finite_map_fingerprint": row.get("finite_map_fingerprint"),
            "failure": _failure_signature(row),
        }
    return _hash({"question_fingerprint": question_fingerprint, "behavior": behavior}), finite_map


def _extract_candidates(result: dict) -> tuple[dict, ...]:
    if isinstance(result.get("ranked_candidates"), list):
        rows = result["ranked_candidates"]
    else:
        rows = list(result.get("exact_candidates", [])) + list(result.get("near_misses", []))
    unique = {}
    for row in rows:
        if isinstance(row, dict) and isinstance(row.get("program"), str):
            unique.setdefault(row["program"], row)
    return tuple(unique.values())


class ResearchMemoryStore:
    """SQLite history for generated transformation candidates and their evidence.

    Program keys use the transformation grammar's normalized program string
    and grammar version. A matching finite-map fingerprint means equality on
    the recorded finite source sets only; it is not a symbolic equivalence
    proof.
    """

    def __init__(self, database: str | os.PathLike[str] | None = None):
        self.path = Path(database or default_research_memory_database()).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA synchronous=FULL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS research_runs (
                    run_id TEXT PRIMARY KEY,
                    question_fingerprint TEXT NOT NULL,
                    question_format TEXT NOT NULL,
                    grammar_version TEXT NOT NULL,
                    engine_version TEXT NOT NULL,
                    classification TEXT NOT NULL,
                    result_digest TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    provenance_json TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    novelty_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS research_runs_question
                    ON research_runs(question_fingerprint, created_at);
                CREATE TABLE IF NOT EXISTS research_candidates (
                    candidate_id TEXT PRIMARY KEY,
                    grammar_version TEXT NOT NULL,
                    canonical_program TEXT NOT NULL,
                    first_seen_at REAL NOT NULL,
                    last_seen_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS candidate_observations (
                    run_id TEXT NOT NULL REFERENCES research_runs(run_id) ON DELETE CASCADE,
                    candidate_id TEXT NOT NULL REFERENCES research_candidates(candidate_id),
                    question_fingerprint TEXT NOT NULL,
                    behavior_key TEXT NOT NULL,
                    finite_map INTEGER NOT NULL,
                    novelty TEXT NOT NULL,
                    candidate_json TEXT NOT NULL,
                    PRIMARY KEY(run_id, candidate_id)
                );
                CREATE INDEX IF NOT EXISTS candidate_observations_program
                    ON candidate_observations(candidate_id, question_fingerprint);
                CREATE INDEX IF NOT EXISTS candidate_observations_behavior
                    ON candidate_observations(question_fingerprint, behavior_key);
                """
            )
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, MEMORY_SCHEMA_VERSION):
                raise ValueError("research-memory database uses an unsupported schema version")
            connection.execute(f"PRAGMA user_version={MEMORY_SCHEMA_VERSION}")

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
    def _question_metadata(question):
        from ac.discovery.transformation_search import TransformationSearchSpec
        from ac.discovery.transformation_family import TransformationFamilySearchSpec
        if not isinstance(question, (TransformationSearchSpec, TransformationFamilySearchSpec)):
            raise ValueError("research memory currently records transformation search questions")
        serialized = question.to_dict()
        return question.fingerprint, serialized["format"], question.grammar_version

    def record_result(
        self,
        question,
        result: dict,
        *,
        run_id: str | None = None,
        provenance: dict | None = None,
        engine_version: str = MEMORY_ENGINE_VERSION,
    ) -> dict:
        if not isinstance(result, dict):
            raise ValueError("research result must be a JSON object")
        if provenance is None:
            provenance = {}
        if not isinstance(provenance, dict):
            raise ValueError("provenance must be a JSON object")
        if not isinstance(engine_version, str) or not engine_version:
            raise ValueError("engine_version must be a nonempty string")
        question_fingerprint, question_format, grammar_version = self._question_metadata(question)
        identifier = run_id or uuid.uuid4().hex
        if not isinstance(identifier, str) or not identifier or len(identifier) > 128:
            raise ValueError("run_id must be a nonempty string of at most 128 characters")
        classification = provenance.get("classification", "unclassified_bounded_run")
        if not isinstance(classification, str) or not classification:
            raise ValueError("provenance classification must be a nonempty string")
        encoded_result = _json(result)
        result_digest = hashlib.sha256(encoded_result.encode("utf-8")).hexdigest()
        encoded_provenance = _json(provenance)
        candidates = _extract_candidates(result)

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            prior_run = connection.execute(
                "SELECT question_fingerprint,result_digest,novelty_json FROM research_runs WHERE run_id=?",
                (identifier,),
            ).fetchone()
            if prior_run is not None:
                if prior_run["question_fingerprint"] != question_fingerprint or prior_run["result_digest"] != result_digest:
                    connection.rollback()
                    raise ValueError("run_id already exists with a different question or result")
                report = json.loads(prior_run["novelty_json"])
                report["idempotent"] = True
                connection.commit()
                return report

            prepared = []
            seen_candidate_ids = set()
            for row in candidates:
                program = row["program"]
                candidate_id = _hash({"grammar_version": grammar_version, "program": program})
                if candidate_id in seen_candidate_ids:
                    continue
                seen_candidate_ids.add(candidate_id)
                behavior_key, finite_map = _behavior_signature(row, question_fingerprint)
                same_question_program = connection.execute(
                    "SELECT run_id FROM candidate_observations WHERE candidate_id=? AND question_fingerprint=? ORDER BY rowid LIMIT 1",
                    (candidate_id, question_fingerprint),
                ).fetchone()
                same_map = connection.execute(
                    "SELECT run_id,candidate_id FROM candidate_observations WHERE question_fingerprint=? AND behavior_key=? AND finite_map=1 AND candidate_id<>? ORDER BY rowid LIMIT 1",
                    (question_fingerprint, behavior_key, candidate_id),
                ).fetchone() if finite_map else None
                same_failure = connection.execute(
                    "SELECT run_id,candidate_id FROM candidate_observations WHERE question_fingerprint=? AND behavior_key=? AND candidate_id<>? ORDER BY rowid LIMIT 1",
                    (question_fingerprint, behavior_key, candidate_id),
                ).fetchone() if not finite_map else None
                elsewhere = connection.execute(
                    "SELECT run_id FROM candidate_observations WHERE candidate_id=? ORDER BY rowid LIMIT 1",
                    (candidate_id,),
                ).fetchone()
                if same_question_program is not None:
                    novelty, prior = "exact_program_duplicate", same_question_program["run_id"]
                elif same_map is not None:
                    novelty, prior = "same_finite_map", same_map["run_id"]
                elif same_failure is not None:
                    novelty, prior = "same_failure_signature", same_failure["run_id"]
                elif elsewhere is not None:
                    novelty, prior = "new_application_of_known_transformation", elsewhere["run_id"]
                else:
                    novelty, prior = "new_transformation", None
                prepared.append({
                    "candidate_id": candidate_id,
                    "program": program,
                    "behavior_key": behavior_key,
                    "finite_map": finite_map,
                    "novelty": novelty,
                    "prior_run_id": prior,
                    "candidate_json": _json(row),
                })

            now = time.time()
            counts = {
                "new_transformation": 0,
                "new_application_of_known_transformation": 0,
                "exact_program_duplicate": 0,
                "same_finite_map": 0,
                "same_failure_signature": 0,
            }
            novelty_rows = []
            for item in prepared:
                counts[item["novelty"]] += 1
                novelty_rows.append({
                    "candidate_id": item["candidate_id"],
                    "program": item["program"],
                    "novelty": item["novelty"],
                    "prior_run_id": item["prior_run_id"],
                    "finite_map_fingerprint": json.loads(item["candidate_json"]).get("finite_map_fingerprint"),
                })
            report = {
                "run_id": identifier,
                "question_fingerprint": question_fingerprint,
                "candidate_count": len(prepared),
                "novelty_counts": counts,
                "candidates": novelty_rows,
                "idempotent": False,
            }
            connection.execute(
                """INSERT INTO research_runs(
                    run_id,question_fingerprint,question_format,grammar_version,engine_version,
                    classification,result_digest,created_at,provenance_json,result_json,novelty_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    identifier, question_fingerprint, question_format, grammar_version,
                    engine_version, classification, result_digest, now, encoded_provenance,
                    encoded_result, _json(report),
                ),
            )
            for item in prepared:
                connection.execute(
                    """INSERT INTO research_candidates(candidate_id,grammar_version,canonical_program,first_seen_at,last_seen_at)
                       VALUES(?,?,?,?,?)
                       ON CONFLICT(candidate_id) DO UPDATE SET last_seen_at=excluded.last_seen_at""",
                    (item["candidate_id"], grammar_version, item["program"], now, now),
                )
                connection.execute(
                    """INSERT INTO candidate_observations(
                        run_id,candidate_id,question_fingerprint,behavior_key,finite_map,novelty,candidate_json
                    ) VALUES(?,?,?,?,?,?,?)""",
                    (
                        identifier, item["candidate_id"], question_fingerprint, item["behavior_key"],
                        int(item["finite_map"]), item["novelty"], item["candidate_json"],
                    ),
                )
            connection.commit()
        return report

    def get_run(self, run_id: str) -> dict:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM research_runs WHERE run_id=?", (run_id,)).fetchone()
        if row is None:
            raise KeyError(run_id)
        return {
            "run_id": row["run_id"],
            "question_fingerprint": row["question_fingerprint"],
            "question_format": row["question_format"],
            "grammar_version": row["grammar_version"],
            "engine_version": row["engine_version"],
            "classification": row["classification"],
            "created_at": row["created_at"],
            "provenance": json.loads(row["provenance_json"]),
            "result": json.loads(row["result_json"]),
            "novelty": json.loads(row["novelty_json"]),
        }

    def recent_runs(self, *, limit: int = 100) -> tuple[dict, ...]:
        if type(limit) is not int or not 1 <= limit <= 10_000:
            raise ValueError("limit must be an integer from 1 through 10000")
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT run_id,question_fingerprint,question_format,grammar_version,classification,created_at,novelty_json "
                "FROM research_runs ORDER BY created_at DESC,run_id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return tuple({
            "run_id": row["run_id"],
            "question_fingerprint": row["question_fingerprint"],
            "question_format": row["question_format"],
            "grammar_version": row["grammar_version"],
            "classification": row["classification"],
            "created_at": row["created_at"],
            "novelty": json.loads(row["novelty_json"]),
        } for row in rows)

    def candidate_history(self, candidate_id: str) -> tuple[dict, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT observations.run_id,observations.question_fingerprint,observations.behavior_key,
                          observations.novelty,observations.finite_map,observations.candidate_json,
                          runs.created_at,runs.classification
                   FROM candidate_observations AS observations
                   JOIN research_runs AS runs USING(run_id)
                   WHERE observations.candidate_id=? ORDER BY runs.created_at,runs.run_id""",
                (candidate_id,),
            ).fetchall()
        return tuple({
            "run_id": row["run_id"],
            "question_fingerprint": row["question_fingerprint"],
            "behavior_key": row["behavior_key"],
            "novelty": row["novelty"],
            "finite_map": bool(row["finite_map"]),
            "candidate": json.loads(row["candidate_json"]),
            "created_at": row["created_at"],
            "classification": row["classification"],
        } for row in rows)
