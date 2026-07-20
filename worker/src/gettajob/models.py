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
