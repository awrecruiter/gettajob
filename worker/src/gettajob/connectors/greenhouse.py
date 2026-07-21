import re
from html import unescape
from typing import Iterable, Optional

import requests

from gettajob.connectors._html import strip_html as _strip_html
from gettajob.connectors.base import Connector
from gettajob.models import Job


_PAY_RANGE_RE = re.compile(
    r'class="pay-range".*?\$([\d,]+).*?\$([\d,]+)', re.DOTALL
)


def _extract_pay_range(html: Optional[str]) -> tuple[Optional[int], Optional[int]]:
    """Anthropic/Airbnb-style greenhouse boards embed comp in <div class="pay-range">."""
    if not html:
        return None, None
    m = _PAY_RANGE_RE.search(unescape(html))
    if not m:
        return None, None
    def _to_int(s: str) -> Optional[int]:
        try:
            return int(s.replace(",", ""))
        except ValueError:
            return None
    return _to_int(m.group(1)), _to_int(m.group(2))


class GreenhouseConnector(Connector):
    source = "greenhouse"

    def __init__(self, slug: str, company_name: str) -> None:
        self.slug = slug
        self.company_name = company_name

    @property
    def identifier(self) -> str:
        return self.slug

    def fetch(self) -> Iterable[Job]:
        url = f"https://boards-api.greenhouse.io/v1/boards/{self.slug}/jobs"
        r = requests.get(url, params={"content": "true"}, timeout=30)
        r.raise_for_status()
        for j in r.json().get("jobs", []):
            location = (j.get("location") or {}).get("name")
            content = j.get("content")
            salary_min, salary_max = _extract_pay_range(content)
            yield Job(
                external_id=str(j["id"]),
                source=self.source,
                company=self.company_name,
                title=j.get("title", ""),
                location=location,
                salary_min=salary_min,
                salary_max=salary_max,
                description=_strip_html(content),
                job_url=j.get("absolute_url"),
                application_url=j.get("absolute_url"),
                posted_at=j.get("updated_at"),
                raw=j,
            )
