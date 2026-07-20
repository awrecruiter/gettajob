from datetime import datetime, timezone
from typing import Iterable

import requests

from gettajob.connectors.base import Connector
from gettajob.models import Job


class LeverConnector(Connector):
    source = "lever"

    def __init__(self, slug: str, company_name: str) -> None:
        self.slug = slug
        self.company_name = company_name

    @property
    def identifier(self) -> str:
        return self.slug

    def fetch(self) -> Iterable[Job]:
        url = f"https://api.lever.co/v0/postings/{self.slug}"
        r = requests.get(url, params={"mode": "json"}, timeout=30)
        r.raise_for_status()
        for p in r.json():
            cats = p.get("categories") or {}
            location = cats.get("location")
            remote = "remote" in location.lower() if location else None
            salary = p.get("salaryRange") or {}
            posted_ms = p.get("createdAt")
            posted_at = None
            if isinstance(posted_ms, int):
                posted_at = datetime.fromtimestamp(posted_ms / 1000, tz=timezone.utc).isoformat()
            yield Job(
                external_id=p["id"],
                source=self.source,
                company=self.company_name,
                title=p.get("text", ""),
                location=location,
                remote=remote,
                salary_min=salary.get("min"),
                salary_max=salary.get("max"),
                description=p.get("descriptionPlain") or p.get("description"),
                job_url=p.get("hostedUrl"),
                application_url=p.get("applyUrl") or p.get("hostedUrl"),
                posted_at=posted_at,
                raw=p,
            )
