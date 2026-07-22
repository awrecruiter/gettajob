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
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS years_required SMALLINT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS shortlisted_at TIMESTAMPTZ;

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
        self._dict_row = dict_row
        self._url = url
        self.conn = self._connect()

    def _connect(self):
        # Neon closes idle SSL connections; keepalives keep the socket alive
        # across the ~200ms gaps between Workday detail-fetch upserts.
        return self._psycopg.connect(
            self._url,
            row_factory=self._dict_row,
            autocommit=True,
            keepalives=1,
            keepalives_idle=30,
            keepalives_interval=10,
            keepalives_count=5,
        )

    def _reconnect_if_closed(self) -> None:
        if self.conn.closed:
            self.conn = self._connect()

    def _execute(self, sql: str, params=None, *, fetch: Optional[str] = None):
        """Execute one statement with one reconnect+retry on connection loss.

        fetch: None (no fetch), 'one' (fetchone), or 'all' (fetchall as list).
        """
        for attempt in range(2):
            try:
                self._reconnect_if_closed()
                with self.conn.cursor() as cur:
                    cur.execute(sql, params)
                    if fetch == "one":
                        return cur.fetchone()
                    if fetch == "all":
                        return list(cur.fetchall())
                    return None
            except self._psycopg.OperationalError:
                if attempt == 0:
                    self.conn = self._connect()
                    continue
                raise

    def init(self) -> None:
        self._execute(SCHEMA)

    def upsert_job(self, job: Job) -> bool:
        from gettajob.clearance import extract_clearance_required
        from gettajob.experience import extract_years_required

        raw = self._psycopg.types.json.Jsonb(job.raw) if job.raw is not None else None
        years_required = extract_years_required(job.description)
        clearance_required = extract_clearance_required(job.description)
        now = _now()
        row = self._execute(
            """
            INSERT INTO jobs (
                external_id, source, company, title, location, remote,
                salary_min, salary_max, description, job_url,
                application_url, posted_at, first_seen, last_seen, raw,
                years_required, clearance_required
            ) VALUES (
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s
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
                    raw = EXCLUDED.raw,
                    years_required = EXCLUDED.years_required,
                    -- Preserve scorer output when regex doesn't detect one.
                    clearance_required = COALESCE(
                        EXCLUDED.clearance_required, jobs.clearance_required
                    )
            RETURNING (xmax = 0) AS inserted
            """,
            (
                job.external_id, job.source, job.company, job.title,
                job.location, job.remote,
                job.salary_min, job.salary_max, job.description,
                job.job_url, job.application_url, job.posted_at,
                now, now, raw,
                years_required, clearance_required,
            ),
            fetch="one",
        )
        return bool(row["inserted"])

    def start_run(self, source: str, identifier: Optional[str]) -> int:
        row = self._execute(
            "INSERT INTO connector_runs (source, identifier, started_at) VALUES (%s, %s, %s) RETURNING id",
            (source, identifier, _now()),
            fetch="one",
        )
        return int(row["id"])

    def finish_run(
        self,
        run_id: int,
        status: str,
        jobs_found: int,
        jobs_new: int,
        error_message: Optional[str] = None,
    ) -> None:
        self._execute(
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
        return self._execute(query, params, fetch="all")

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
        return self._execute(query, params, fetch="all")

    def get_jobs_by_ids(self, ids: list[int]) -> list[dict]:
        if not ids:
            return []
        query = (
            "SELECT id, source, company, title, location, remote, salary_min, "
            "salary_max, description FROM jobs WHERE id = ANY(%s)"
        )
        return self._execute(query, (list(ids),), fetch="all")

    def update_score(self, score: Score) -> None:
        self._execute(
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
