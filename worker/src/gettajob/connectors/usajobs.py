from typing import Iterable, Optional

import requests

from gettajob.config import USAJobsQuery
from gettajob.connectors.base import Connector
from gettajob.models import Job


class USAJobsConnector(Connector):
    source = "usajobs"

    def __init__(self, query: USAJobsQuery, user_agent: str, api_key: str) -> None:
        self.query = query
        self.user_agent = user_agent
        self.api_key = api_key

    @property
    def identifier(self) -> str:
        return self.query.keyword or self.query.location or "all"

    def fetch(self) -> Iterable[Job]:
        headers = {
            "Host": "data.usajobs.gov",
            "User-Agent": self.user_agent,
            "Authorization-Key": self.api_key,
        }
        page = 1
        while True:
            params: dict = {
                "ResultsPerPage": self.query.results_per_page,
                "Page": page,
            }
            if self.query.keyword:
                params["Keyword"] = self.query.keyword
            if self.query.location:
                params["LocationName"] = self.query.location

            r = requests.get(
                "https://data.usajobs.gov/api/search",
                headers=headers,
                params=params,
                timeout=30,
            )
            r.raise_for_status()
            result = r.json().get("SearchResult", {})
            items = result.get("SearchResultItems", [])
            for item in items:
                d = item.get("MatchedObjectDescriptor", {}) or {}
                salary_min, salary_max = _extract_salary(d)
                locations = d.get("PositionLocation") or []
                loc = ", ".join(l.get("LocationName", "") for l in locations) or None
                apply_uris = d.get("ApplyURI") or []
                yield Job(
                    external_id=str(item.get("MatchedObjectId") or d.get("PositionID") or ""),
                    source=self.source,
                    company=d.get("OrganizationName") or "US Federal Government",
                    title=d.get("PositionTitle", ""),
                    location=loc,
                    salary_min=salary_min,
                    salary_max=salary_max,
                    description=(d.get("UserArea") or {}).get("Details", {}).get("JobSummary"),
                    job_url=d.get("PositionURI"),
                    application_url=apply_uris[0] if apply_uris else d.get("PositionURI"),
                    posted_at=d.get("PublicationStartDate"),
                    raw=item,
                )
            count = int(result.get("SearchResultCount", 0))
            total = int(result.get("SearchResultCountAll", 0))
            if count == 0 or page * self.query.results_per_page >= total:
                break
            page += 1


def _extract_salary(d: dict) -> tuple[Optional[int], Optional[int]]:
    remun = d.get("PositionRemuneration") or []
    if not remun:
        return None, None
    r = remun[0]
    def _num(v) -> Optional[int]:
        try:
            n = int(float(v))
            return n or None
        except (TypeError, ValueError):
            return None
    return _num(r.get("MinimumRange")), _num(r.get("MaximumRange"))
