from pathlib import Path
from typing import Optional, Protocol, runtime_checkable

from gettajob.models import Job, Score


@runtime_checkable
class Database(Protocol):
    def init(self) -> None: ...
    def upsert_job(self, job: Job) -> bool: ...
    def start_run(self, source: str, identifier: Optional[str]) -> int: ...
    def finish_run(
        self,
        run_id: int,
        status: str,
        jobs_found: int,
        jobs_new: int,
        error_message: Optional[str] = None,
    ) -> None: ...
    def list_jobs(
        self,
        limit: int = 50,
        company: Optional[str] = None,
        source: Optional[str] = None,
        min_score: Optional[int] = None,
    ) -> list: ...
    def list_unscored(self, limit: int, source: Optional[str] = None) -> list: ...
    def get_jobs_by_ids(self, ids: list[int]) -> list: ...
    def update_score(self, score: Score) -> None: ...
    def close(self) -> None: ...


def make_database(url_or_path: str) -> Database:
    """Build a SQLite or Postgres backend based on the URL scheme."""
    s = str(url_or_path)
    if s.startswith(("postgres://", "postgresql://")):
        from gettajob.db_postgres import PostgresDatabase
        return PostgresDatabase(s)
    from gettajob.db_sqlite import SqliteDatabase
    return SqliteDatabase(Path(url_or_path))
