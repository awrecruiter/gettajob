from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Job:
    external_id: str
    source: str
    company: str
    title: str
    location: Optional[str] = None
    remote: Optional[bool] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    description: Optional[str] = None
    job_url: Optional[str] = None
    application_url: Optional[str] = None
    posted_at: Optional[str] = None
    raw: Optional[dict] = field(default=None, repr=False)


@dataclass
class Score:
    """Output of the Should-I-Apply scorer for a single job (PRD §5 Stage 2)."""
    job_id: int
    score: int  # 0-100
    salary_estimate: Optional[int] = None
    clearance_required: Optional[bool] = None
    travel_pct: Optional[int] = None
    remote_scored: Optional[bool] = None
    uses_python: Optional[bool] = None
    uses_ai: Optional[bool] = None
    customer_facing: Optional[bool] = None
    government: Optional[bool] = None
    uses_cpp: Optional[bool] = None
    could_get_interview: Optional[bool] = None
    reasoning: Optional[str] = None
    model: Optional[str] = None
