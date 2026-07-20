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


def cmd_init(args: argparse.Namespace) -> int:
    target = _resolve_db_target(args.db)
    db = make_database(target)
    db.init()
    print(f"Initialized database at {target}")
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
    rows = db.list_jobs(limit=args.limit, company=args.company, source=args.source)
    for r in rows:
        salary = ""
        if r["salary_min"] or r["salary_max"]:
            salary = f" | ${r['salary_min'] or '?'}–${r['salary_max'] or '?'}"
        title = (r["title"] or "")[:60]
        loc = (r["location"] or "")[:25]
        print(f"{r['source']:10} {r['company']:20} {title:60} {loc:25}{salary}")
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

    args = parser.parse_args(argv)

    if args.command == "init":
        return cmd_init(args)
    if args.command == "run":
        return cmd_run(args)
    if args.command == "list":
        return cmd_list(args)
    parser.error(f"Unknown command: {args.command}")
    return 1
