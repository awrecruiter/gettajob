import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from gettajob.config import CompanyRef, load_config
from gettajob.connectors.ashby import AshbyConnector
from gettajob.connectors.base import Connector
from gettajob.connectors.greenhouse import GreenhouseConnector
from gettajob.connectors.lever import LeverConnector
from gettajob.connectors.usajobs import USAJobsConnector
from gettajob.db import Database, make_database

DEFAULT_DB = "gettajob.db"
DEFAULT_CONFIG = Path("config.json")

CONNECTOR_TYPES: dict[str, type[Connector]] = {
    "greenhouse": GreenhouseConnector,
    "lever": LeverConnector,
    "ashby": AshbyConnector,
}


def build_company_connector(company: CompanyRef) -> Connector:
    cls = CONNECTOR_TYPES[company.source]
    return cls(company.slug, company.name)


def _resolve_db_target(cli_arg: str | None) -> str:
    if cli_arg:
        return cli_arg
    return os.getenv("DATABASE_URL") or DEFAULT_DB


def _open_db(cli_arg: str | None) -> Database:
    target = _resolve_db_target(cli_arg)
    return make_database(target)


def _redact_db_target(target: str) -> str:
    if target.startswith(("postgres://", "postgresql://")):
        from urllib.parse import urlparse
        u = urlparse(target)
        return f"{u.scheme}://{u.hostname}{u.path}" if u.hostname else target
    return target


def cmd_init(args: argparse.Namespace) -> int:
    target = _resolve_db_target(args.db)
    db = make_database(target)
    db.init()
    print(f"Initialized database at {_redact_db_target(target)}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    db = _open_db(args.db)
    db.init()

    connectors: list[Connector] = []
    for c in config.companies:
        if args.source and c.source != args.source:
            continue
        if c.source not in CONNECTOR_TYPES:
            print(f"Warning: unknown source '{c.source}' for {c.name}", file=sys.stderr)
            continue
        connectors.append(build_company_connector(c))

    if not args.source or args.source == "usajobs":
        if config.usajobs_api_key and config.usajobs_user_agent:
            for q in config.usajobs_queries:
                connectors.append(
                    USAJobsConnector(q, config.usajobs_user_agent, config.usajobs_api_key)
                )
        elif args.source == "usajobs":
            print(
                "USAJobs credentials not set — populate USAJOBS_USER_AGENT and USAJOBS_API_KEY",
                file=sys.stderr,
            )
            return 1

    if not connectors:
        print("No connectors to run — check config.json and --source flag", file=sys.stderr)
        return 1

    total_found = 0
    total_new = 0
    for c in connectors:
        run_id = db.start_run(c.source, c.identifier)
        try:
            jobs = list(c.fetch())
            new_count = sum(1 for j in jobs if db.upsert_job(j))
            db.finish_run(run_id, "ok", len(jobs), new_count)
            total_found += len(jobs)
            total_new += new_count
            print(f"[{c.source}:{c.identifier}] {len(jobs)} jobs, {new_count} new")
        except Exception as e:
            db.finish_run(run_id, "error", 0, 0, str(e))
            print(f"[{c.source}:{c.identifier}] ERROR: {e}", file=sys.stderr)

    print(f"\nTotal: {total_found} jobs, {total_new} new")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    db = _open_db(args.db)
    rows = db.list_jobs(
        limit=args.limit,
        company=args.company,
        source=args.source,
        min_score=args.min_score,
    )
    for r in rows:
        salary = ""
        if r["salary_min"] or r["salary_max"]:
            salary = f" | ${r['salary_min'] or '?'}–${r['salary_max'] or '?'}"
        title = (r["title"] or "")[:60]
        loc = (r["location"] or "")[:25]
        score = r["score"] if "score" in r.keys() else None
        score_col = f" [{score:>3}]" if score is not None else "  [ - ]"
        print(f"{score_col} {r['source']:10} {r['company']:20} {title:60} {loc:25}{salary}")
    return 0


def cmd_score(args: argparse.Namespace) -> int:
    try:
        import anthropic
    except ImportError:
        print(
            "anthropic SDK is required. Install with: pip install 'gettajob[scorer]'",
            file=sys.stderr,
        )
        return 1
    from gettajob.scorer import ScorerConfig, score_jobs

    db = _open_db(args.db)
    db.init()
    if args.rescore:
        jobs = list(db.get_jobs_by_ids(args.rescore))
        missing = set(args.rescore) - {row["id"] for row in jobs}
        if missing:
            print(f"Warning: job ids not found: {sorted(missing)}", file=sys.stderr)
        if not jobs:
            print("No matching jobs.")
            return 0
    else:
        jobs = list(db.list_unscored(limit=args.limit, source=args.source))
        if not jobs:
            print("No unscored jobs.")
            return 0

    normalized = [dict(row) for row in jobs]
    print(f"Scoring {len(normalized)} jobs with {args.model} (batch={args.batch_size})…")

    client = anthropic.Anthropic()
    cfg = ScorerConfig(model=args.model, batch_size=args.batch_size)

    scored_total = 0
    for batch_scores, meta in score_jobs(client, normalized, cfg):
        for s in batch_scores:
            db.update_score(s)
        scored_total += len(batch_scores)
        print(f"  batch: {meta['batch_size']} jobs → {len(batch_scores)} scored (running total {scored_total})")

    print(f"\nDone. Scored {scored_total} jobs.")
    return 0


def main(argv: list[str] | None = None) -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(prog="gettajob", description="Automated job hunting — v1")
    parser.add_argument(
        "--db",
        default=None,
        help="SQLite path or Postgres URL. Defaults to $DATABASE_URL, then ./gettajob.db",
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Config file path")

    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="Initialize the database")

    p_run = sub.add_parser("run", help="Run connectors and store jobs")
    p_run.add_argument(
        "--source",
        choices=["greenhouse", "lever", "ashby", "usajobs"],
        help="Only run this source",
    )

    p_list = sub.add_parser("list", help="List recent jobs")
    p_list.add_argument("--limit", type=int, default=50)
    p_list.add_argument("--company")
    p_list.add_argument("--source")
    p_list.add_argument("--min-score", type=int, default=None, help="Only show jobs at or above this score")

    p_score = sub.add_parser("score", help="Score unscored jobs via Claude")
    p_score.add_argument("--limit", type=int, default=50, help="Max jobs to score in this run")
    p_score.add_argument("--source", help="Only score jobs from this source")
    p_score.add_argument("--batch-size", type=int, default=10)
    p_score.add_argument("--model", default="claude-haiku-4-5")
    p_score.add_argument(
        "--rescore",
        type=int,
        action="append",
        metavar="JOB_ID",
        help="Re-score specific job IDs (repeatable). Overrides --limit/--source.",
    )

    args = parser.parse_args(argv)

    if args.command == "init":
        return cmd_init(args)
    if args.command == "run":
        return cmd_run(args)
    if args.command == "list":
        return cmd_list(args)
    if args.command == "score":
        return cmd_score(args)
    parser.error(f"Unknown command: {args.command}")
    return 1
