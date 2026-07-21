import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


@dataclass
class CompanyRef:
    source: str
    slug: str
    name: str


@dataclass
class USAJobsQuery:
    keyword: Optional[str] = None
    location: Optional[str] = None
    results_per_page: int = 50


@dataclass
class WorkdayTenant:
    host: str
    tenant: str
    site: str
    name: str


@dataclass
class Config:
    companies: list[CompanyRef] = field(default_factory=list)
    usajobs_queries: list[USAJobsQuery] = field(default_factory=list)
    usajobs_user_agent: Optional[str] = None
    usajobs_api_key: Optional[str] = None
    workday_tenants: list[WorkdayTenant] = field(default_factory=list)


def load_config(path: Path) -> Config:
    load_dotenv()
    with open(path) as f:
        data = json.load(f)
    return Config(
        companies=[CompanyRef(**c) for c in data.get("companies", [])],
        usajobs_queries=[USAJobsQuery(**q) for q in data.get("usajobs_queries", [])],
        usajobs_user_agent=os.getenv("USAJOBS_USER_AGENT"),
        usajobs_api_key=os.getenv("USAJOBS_API_KEY"),
        workday_tenants=[WorkdayTenant(**w) for w in data.get("workday_tenants", [])],
    )
