from typing import Iterable, Optional

import requests

from gettajob.connectors.base import Connector
from gettajob.models import Job


class AshbyConnector(Connector):
    source = "ashby"

    def __init__(self, slug: str, company_name: str) -> None:
        self.slug = slug
        self.company_name = company_name

    @property
    def identifier(self) -> str:
        return self.slug

    def fetch(self) -> Iterable[Job]:
        url = f"https://api.ashbyhq.com/posting-api/job-board/{self.slug}"
        r = requests.get(url, params={"includeCompensation": "true"}, timeout=30)
        r.raise_for_status()
        for j in r.json().get("jobs", []):
            salary_min, salary_max = _extract_salary(j.get("compensation") or {})
            yield Job(
                external_id=j["id"],
                source=self.source,
                company=self.company_name,
                title=j.get("title", ""),
                location=j.get("location"),
                remote=j.get("isRemote"),
                salary_min=salary_min,
                salary_max=salary_max,
                description=j.get("descriptionPlain") or j.get("description"),
                job_url=j.get("jobUrl"),
                application_url=j.get("applyUrl") or j.get("jobUrl"),
                posted_at=j.get("publishedDate") or j.get("publishedAt"),
                raw=j,
            )


def _extract_salary(comp: dict) -> tuple[Optional[int], Optional[int]]:
    """Best-effort salary extraction from Ashby's compensation payload.

    Ashby exposes several compensation shapes. We scan components for min/max
    values and return the overall range."""
    mins: list[float] = []
    maxs: list[float] = []
    for tier in comp.get("compensationTiers") or []:
        for c in tier.get("components") or []:
            for key, bucket in (("minValue", mins), ("maxValue", maxs)):
                v = c.get(key)
                if isinstance(v, dict):
                    v = v.get("value")
                if isinstance(v, (int, float)):
                    bucket.append(float(v))
    return (
        int(min(mins)) if mins else None,
        int(max(maxs)) if maxs else None,
    )
