from html import unescape
from html.parser import HTMLParser
from typing import Iterable, Optional

import requests

from gettajob.connectors.base import Connector
from gettajob.models import Job


class _Stripper(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def _strip_html(html: Optional[str]) -> Optional[str]:
    if not html:
        return html
    s = _Stripper()
    s.feed(html)
    return unescape(" ".join(s.parts)).strip()


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
            yield Job(
                external_id=str(j["id"]),
                source=self.source,
                company=self.company_name,
                title=j.get("title", ""),
                location=location,
                description=_strip_html(j.get("content")),
                job_url=j.get("absolute_url"),
                application_url=j.get("absolute_url"),
                posted_at=j.get("updated_at"),
                raw=j,
            )
