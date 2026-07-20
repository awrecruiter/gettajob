import json
from datetime import datetime, timezone
from typing import Optional

from gettajob.models import Job, Score

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id BIGSERIAL PRIMARY KEY,
    external_id TEXT NOT NULL,
    source TEXT NOT NULL,
    company TEXT NOT NULL,
    title TEXT NOT NULL,
    location TEXT,
    remote BOOLEAN,
    salary_min BIGINT,
    salary_max BIGINT,
    description TEXT,
    job_url TEXT,
    application_url TEXT,
    posted_at TIMESTAMPTZ,
    first_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    raw JSONB,
    UNIQUE(source, external_id)
);

CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company);
CREATE INDEX IF NOT EXISTS idx_jobs_last_seen ON jobs(last_seen);

ALTER TABLE jobs ADD COLUMN IF NOT EXISTS score SMALLINT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS salary_estimate BIGINT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS clearance_required BOOLEAN;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS travel_pct SMALLINT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS remote_scored BOOLEAN;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS uses_python BOOLEAN;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS uses_ai BOOLEAN;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS customer_facing BOOLEAN;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS government BOOLEAN;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS uses_cpp BOOLEAN;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS could_get_interview BOOLEAN;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS score_reasoning TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS score_model TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS scored_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_jobs_score ON jobs(score DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_jobs_scored_at ON jobs(scored_at) WHERE scored_at IS NULL;

CREATE TABLE IF NOT EXISTS connector_runs (
    id BIGSERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    identifier TEXT,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    status TEXT,
    jobs_found INTEGER,
    jobs_new INTEGER,
    error_message TEXT
);
"""


def _now():
    return datetime.now(timezone.utc)


class PostgresDatabase:
    def __init__(self, url: str) -> None:
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as e:
            raise ImportError(
                "psycopg is required for Postgres. Install with: pip install 'gettajob[postgres]'"
            ) from e
        self._psycopg = psycopg
        # Neon and Vercel both require sslmode=require; leave it to the caller's URL.
        self.conn = psycopg.connect(url, row_factory=dict_row, autocommit=True)

    def init(self) -> None:
        with self.conn.cursor() as cur:
            cur.execute(SCHEMA)

    def upsert_job(self, job: Job) -> bool:
        raw = self._psycopg.types.json.Jsonb(job.raw) if job.raw is not None else None
        now = _now()
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO jobs (
                    external_id, source, company, title, location, remote,
                    salary_min, salary_max, description, job_url,
                    application_url, posted_at, first_seen, last_seen, raw
                ) VALUES (
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s, %s
                )
                ON CONFLICT (source, external_id) DO UPDATE
                    SET title = EXCLUDED.title,
                        location = EXCLUDED.location,
                        remote = EXCLUDED.remote,
                        salary_min = EXCLUDED.salary_min,
                        salary_max = EXCLUDED.salary_max,
                        description = EXCLUDED.description,
                        job_url = EXCLUDED.job_url,
                        application_url = EXCLUDED.application_url,
                        posted_at = EXCLUDED.posted_at,
                        last_seen = EXCLUDED.last_seen,
                        raw = EXCLUDED.raw
                RETURNING (xmax = 0) AS inserted
                """,
                (
                    job.external_id, job.source, job.company, job.title,
                    job.location, job.remote,
                    job.salary_min, job.salary_max, job.description,
                    job.job_url, job.application_url, job.posted_at,
                    now, now, raw,
                ),
            )
            row = cur.fetchone()
            return bool(row["inserted"])

    def start_run(self, source: str, identifier: Optional[str]) -> int:
        with self.conn.cursor() as cur:
            cur.execute(
                "INSERT INTO connector_runs (source, identifier, started_at) VALUES (%s, %s, %s) RETURNING id",
                (source, identifier, _now()),
            )
            row = cur.fetchone()
            return int(row["id"])

    def finish_run(
        self,
        run_id: int,
        status: str,
        jobs_found: int,
        jobs_new: int,
        error_message: Optional[str] = None,
    ) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                UPDATE connector_runs
                   SET finished_at = %s, status = %s, jobs_found = %s,
                       jobs_new = %s, error_message = %s
                 WHERE id = %s
                """,
                (_now(), status, jobs_found, jobs_new, error_message, run_id),
            )

    def list_jobs(
        self,
        limit: int = 50,
        company: Optional[str] = None,
        source: Optional[str] = None,
        min_score: Optional[int] = None,
    ) -> list[dict]:
        query = "SELECT * FROM jobs WHERE TRUE"
        params: list = []
        if company:
            query += " AND company = %s"
            params.append(company)
        if source:
            query += " AND source = %s"
            params.append(source)
        if min_score is not None:
            query += " AND score >= %s"
            params.append(min_score)
        query += " ORDER BY last_seen DESC LIMIT %s"
        params.append(limit)
        with self.conn.cursor() as cur:
            cur.execute(query, params)
            return list(cur.fetchall())

    def list_unscored(self, limit: int, source: Optional[str] = None) -> list[dict]:
        query = (
            "SELECT id, source, company, title, location, remote, salary_min, "
            "salary_max, description FROM jobs WHERE scored_at IS NULL"
        )
        params: list = []
        if source:
            query += " AND source = %s"
            params.append(source)
        query += " ORDER BY last_seen DESC LIMIT %s"
        params.append(limit)
        with self.conn.cursor() as cur:
            cur.execute(query, params)
            return list(cur.fetchall())

    def get_jobs_by_ids(self, ids: list[int]) -> list[dict]:
        if not ids:
            return []
        query = (
            "SELECT id, source, company, title, location, remote, salary_min, "
            "salary_max, description FROM jobs WHERE id = ANY(%s)"
        )
        with self.conn.cursor() as cur:
            cur.execute(query, (list(ids),))
            return list(cur.fetchall())

    def update_score(self, score: Score) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                UPDATE jobs
                   SET score = %s,
                       salary_estimate = %s,
                       clearance_required = %s,
                       travel_pct = %s,
                       remote_scored = %s,
                       uses_python = %s,
                       uses_ai = %s,
                       customer_facing = %s,
                       government = %s,
                       uses_cpp = %s,
                       could_get_interview = %s,
                       score_reasoning = %s,
                       score_model = %s,
                       scored_at = %s
                 WHERE id = %s
                """,
                (
                    score.score, score.salary_estimate, score.clearance_required,
                    score.travel_pct, score.remote_scored, score.uses_python,
                    score.uses_ai, score.customer_facing, score.government,
                    score.uses_cpp, score.could_get_interview,
                    score.reasoning, score.model, _now(), score.job_id,
                ),
            )

    def close(self) -> None:
        self.conn.close()
