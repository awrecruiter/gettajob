"""Workday connector — per-tenant, uses the unofficial `/wday/cxs` search + detail API.

Each Workday customer runs their own tenant at `{tenant}.wd{N}.myworkdayjobs.com`,
so the connector is constructed per host/tenant/site. The list endpoint returns
titles+paths only; a second GET per posting fetches description and salary.
"""
from __future__ import annotations

import json
import re
from typing import Iterable, Optional

import requests

from gettajob.connectors._html import strip_html
from gettajob.connectors.base import Connector
from gettajob.models import Job


_UA = "Mozilla/5.0 (compatible; gettajob/1.0)"

# Workday salary strings look like "$120,000.00 - $150,000.00 Annually" or
# "$120K - $150K". Grab the first two dollar amounts we see.
_SALARY_RE = re.compile(
    r"\$([\d,]+(?:\.\d+)?)\s*[Kk]?\s*[-–—to]+\s*\$([\d,]+(?:\.\d+)?)\s*[Kk]?"
)


def _parse_salary(text: Optional[str]) -> tuple[Optional[int], Optional[int]]:
    if not text:
        return None, None
    m = _SALARY_RE.search(text)
    if not m:
        return None, None
    def _to_int(raw: str, is_k: bool) -> Optional[int]:
        try:
            n = float(raw.replace(",", ""))
        except ValueError:
            return None
        if is_k or n < 1000:  # bare number likely meant thousands
            n *= 1000
        return int(n)
    span_text = m.group(0)
    is_k = "k" in span_text.lower()
    return _to_int(m.group(1), is_k), _to_int(m.group(2), is_k)


class WorkdayConnector(Connector):
    source = "workday"

    def __init__(
        self,
        host: str,
        tenant: str,
        site: str,
        company_name: str,
        # Workday caps page_size at 20 — larger requests get 400.
        page_size: int = 20,
        max_pages: int = 100,
    ) -> None:
        self.host = host
        self.tenant = tenant
        self.site = site
        self.company_name = company_name
        self.page_size = page_size
        self.max_pages = max_pages

    @property
    def identifier(self) -> str:
        return f"{self.tenant}/{self.site}"

    def _base(self, path: str = "") -> str:
        return f"https://{self.host}/wday/cxs/{self.tenant}/{self.site}{path}"

    def fetch(self) -> Iterable[Job]:
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "user-agent": _UA,
        }
        offset = 0
        pages = 0
        while pages < self.max_pages:
            body = json.dumps(
                {
                    "appliedFacets": {},
                    "limit": self.page_size,
                    "offset": offset,
                    "searchText": "",
                }
            )
            r = requests.post(self._base("/jobs"), headers=headers, data=body, timeout=30)
            r.raise_for_status()
            data = r.json() or {}
            postings = data.get("jobPostings") or []
            if not postings:
                break
            for p in postings:
                job = self._fetch_detail(p)
                if job is not None:
                    yield job
            offset += self.page_size
            total = int(data.get("total") or 0)
            if offset >= total:
                break
            pages += 1

    def _fetch_detail(self, posting: dict) -> Optional[Job]:
        external_path = posting.get("externalPath") or ""
        title = posting.get("title", "")
        location = posting.get("locationsText")
        posted_on = posting.get("postedOn")
        bullets = posting.get("bulletFields") or []
        external_id = bullets[0] if bullets else external_path

        detail: dict = {}
        try:
            r = requests.get(
                self._base(external_path),
                headers={"accept": "application/json", "user-agent": _UA},
                timeout=30,
            )
            r.raise_for_status()
            detail = (r.json() or {}).get("jobPostingInfo") or {}
        except requests.RequestException:
            # If detail fetch fails, still yield the listing with what we have.
            pass

        description_html = detail.get("jobDescription")
        description = strip_html(description_html)
        salary_min, salary_max = _parse_salary(description)
        external_url = detail.get("externalUrl") or f"https://{self.host}{external_path}"

        return Job(
            external_id=str(external_id),
            source=self.source,
            company=self.company_name,
            title=title,
            location=location,
            salary_min=salary_min,
            salary_max=salary_max,
            description=description,
            job_url=external_url,
            application_url=external_url,
            posted_at=detail.get("startDate") or posted_on,
            raw={"list": posting, "detail": detail},
        )
