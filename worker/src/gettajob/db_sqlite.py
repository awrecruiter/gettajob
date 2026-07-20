import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from gettajob.models import Job


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


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SqliteDatabase:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row

    def init(self) -> None:
        self.conn.executescript(SCHEMA)
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
    ) -> list[sqlite3.Row]:
        query = "SELECT * FROM jobs WHERE 1=1"
        params: list = []
        if company:
            query += " AND company = ?"
            params.append(company)
        if source:
            query += " AND source = ?"
            params.append(source)
        query += " ORDER BY last_seen DESC LIMIT ?"
        params.append(limit)
        return self.conn.execute(query, params).fetchall()

    def close(self) -> None:
        self.conn.close()
