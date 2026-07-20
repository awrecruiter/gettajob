import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from gettajob.models import Job, Score


SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    external_id TEXT NOT NULL,
    source TEXT NOT NULL,
    company TEXT NOT NULL,
    title TEXT NOT NULL,
    location TEXT,
    remote INTEGER,
    salary_min INTEGER,
    salary_max INTEGER,
    description TEXT,
    job_url TEXT,
    application_url TEXT,
    posted_at TEXT,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    raw_json TEXT,
    UNIQUE(source, external_id)
);

CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company);
CREATE INDEX IF NOT EXISTS idx_jobs_last_seen ON jobs(last_seen);

CREATE TABLE IF NOT EXISTS connector_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    identifier TEXT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT,
    jobs_found INTEGER,
    jobs_new INTEGER,
    error_message TEXT
);
"""

# SQLite doesn't support ALTER TABLE ADD COLUMN IF NOT EXISTS, so migrations
# are declared here and added conditionally in init().
SCORING_COLUMNS: list[tuple[str, str]] = [
    ("score", "INTEGER"),
    ("salary_estimate", "INTEGER"),
    ("clearance_required", "INTEGER"),
    ("travel_pct", "INTEGER"),
    ("remote_scored", "INTEGER"),
    ("uses_python", "INTEGER"),
    ("uses_ai", "INTEGER"),
    ("customer_facing", "INTEGER"),
    ("government", "INTEGER"),
    ("uses_cpp", "INTEGER"),
    ("could_get_interview", "INTEGER"),
    ("score_reasoning", "TEXT"),
    ("score_model", "TEXT"),
    ("scored_at", "TEXT"),
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SqliteDatabase:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row

    def init(self) -> None:
        self.conn.executescript(SCHEMA)
        existing = {row["name"] for row in self.conn.execute("PRAGMA table_info(jobs)")}
        for col, ddl in SCORING_COLUMNS:
            if col not in existing:
                self.conn.execute(f"ALTER TABLE jobs ADD COLUMN {col} {ddl}")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_score ON jobs(score DESC)")
        self.conn.commit()

    def upsert_job(self, job: Job) -> bool:
        """Insert a new job or refresh last_seen on an existing one. Returns True if newly inserted."""
        now = _now()
        raw_json = json.dumps(job.raw) if job.raw is not None else None
        remote = int(job.remote) if job.remote is not None else None

        cur = self.conn.execute(
            "SELECT id FROM jobs WHERE source = ? AND external_id = ?",
            (job.source, job.external_id),
        )
        row = cur.fetchone()
        if row is None:
            self.conn.execute(
                """
                INSERT INTO jobs (
                    external_id, source, company, title, location, remote,
                    salary_min, salary_max, description, job_url,
                    application_url, posted_at, first_seen, last_seen, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job.external_id, job.source, job.company, job.title,
                    job.location, remote,
                    job.salary_min, job.salary_max, job.description,
                    job.job_url, job.application_url, job.posted_at,
                    now, now, raw_json,
                ),
            )
            self.conn.commit()
            return True

        self.conn.execute(
            """
            UPDATE jobs
               SET last_seen = ?, title = ?, location = ?, remote = ?,
                   salary_min = ?, salary_max = ?, description = ?,
                   job_url = ?, application_url = ?, posted_at = ?, raw_json = ?
             WHERE id = ?
            """,
            (
                now, job.title, job.location, remote,
                job.salary_min, job.salary_max, job.description,
                job.job_url, job.application_url, job.posted_at, raw_json,
                row["id"],
            ),
        )
        self.conn.commit()
        return False

    def start_run(self, source: str, identifier: Optional[str]) -> int:
        cur = self.conn.execute(
            "INSERT INTO connector_runs (source, identifier, started_at) VALUES (?, ?, ?)",
            (source, identifier, _now()),
        )
        self.conn.commit()
        return cur.lastrowid

    def finish_run(
        self,
        run_id: int,
        status: str,
        jobs_found: int,
        jobs_new: int,
        error_message: Optional[str] = None,
    ) -> None:
        self.conn.execute(
            """
            UPDATE connector_runs
               SET finished_at = ?, status = ?, jobs_found = ?,
                   jobs_new = ?, error_message = ?
             WHERE id = ?
            """,
            (_now(), status, jobs_found, jobs_new, error_message, run_id),
        )
        self.conn.commit()

    def list_jobs(
        self,
        limit: int = 50,
        company: Optional[str] = None,
        source: Optional[str] = None,
        min_score: Optional[int] = None,
    ) -> list[sqlite3.Row]:
        query = "SELECT * FROM jobs WHERE 1=1"
        params: list = []
        if company:
            query += " AND company = ?"
            params.append(company)
        if source:
            query += " AND source = ?"
            params.append(source)
        if min_score is not None:
            query += " AND score >= ?"
            params.append(min_score)
        query += " ORDER BY last_seen DESC LIMIT ?"
        params.append(limit)
        return self.conn.execute(query, params).fetchall()

    def list_unscored(self, limit: int, source: Optional[str] = None) -> list[sqlite3.Row]:
        query = (
            "SELECT id, source, company, title, location, remote, salary_min, "
            "salary_max, description FROM jobs WHERE scored_at IS NULL"
        )
        params: list = []
        if source:
            query += " AND source = ?"
            params.append(source)
        query += " ORDER BY last_seen DESC LIMIT ?"
        params.append(limit)
        return self.conn.execute(query, params).fetchall()

    def get_jobs_by_ids(self, ids: list[int]) -> list[sqlite3.Row]:
        if not ids:
            return []
        placeholders = ",".join("?" * len(ids))
        query = (
            f"SELECT id, source, company, title, location, remote, salary_min, "
            f"salary_max, description FROM jobs WHERE id IN ({placeholders})"
        )
        return self.conn.execute(query, ids).fetchall()

    def update_score(self, score: Score) -> None:
        remote_scored = None if score.remote_scored is None else int(score.remote_scored)
        bool_cols = {
            "clearance_required": score.clearance_required,
            "uses_python": score.uses_python,
            "uses_ai": score.uses_ai,
            "customer_facing": score.customer_facing,
            "government": score.government,
            "uses_cpp": score.uses_cpp,
            "could_get_interview": score.could_get_interview,
        }
        bool_ints = {k: (None if v is None else int(v)) for k, v in bool_cols.items()}
        self.conn.execute(
            """
            UPDATE jobs
               SET score = ?,
                   salary_estimate = ?,
                   clearance_required = ?,
                   travel_pct = ?,
                   remote_scored = ?,
                   uses_python = ?,
                   uses_ai = ?,
                   customer_facing = ?,
                   government = ?,
                   uses_cpp = ?,
                   could_get_interview = ?,
                   score_reasoning = ?,
                   score_model = ?,
                   scored_at = ?
             WHERE id = ?
            """,
            (
                score.score, score.salary_estimate, bool_ints["clearance_required"],
                score.travel_pct, remote_scored, bool_ints["uses_python"],
                bool_ints["uses_ai"], bool_ints["customer_facing"],
                bool_ints["government"], bool_ints["uses_cpp"],
                bool_ints["could_get_interview"],
                score.reasoning, score.model, _now(), score.job_id,
            ),
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()
