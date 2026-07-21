"""ATS detector — resolve a company URL to a supported connector config.

Given `boozallen.com/careers` or `https://boards.greenhouse.io/anthropic`,
returns a JSON blob you can paste into config.json under `companies` or
`workday_tenants`.
"""
from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urlparse

import requests

_UA = "Mozilla/5.0 (compatible; gettajob-detector/1.0)"

# ATS URL fingerprints. `slug` is the tenant/board identifier.
_ATS_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("greenhouse", re.compile(r"boards\.greenhouse\.io/(?:embed/job_board\?for=)?([a-z0-9_-]+)", re.I)),
    ("greenhouse", re.compile(r"boards-api\.greenhouse\.io/v1/boards/([a-z0-9_-]+)", re.I)),
    ("lever", re.compile(r"(?:jobs|api)\.lever\.co/(?:v0/postings/)?([a-z0-9_-]+)", re.I)),
    ("ashby", re.compile(r"(?:jobs|api)\.ashbyhq\.com/(?:posting-api/job-board/)?([a-z0-9_-]+)", re.I)),
]

# Workday URLs need three pieces (host, tenant, site) and the tenant in the
# path is always lowercased, even when the subdomain is capitalized.
_WORKDAY_RE = re.compile(
    r"([a-z0-9-]+)\.(wd\d+)\.myworkdayjobs\.com(?:/[a-z]{2}(?:-[A-Z]{2})?)?/([A-Za-z0-9_]+)",
    re.I,
)


def _match_ats(text: str) -> Optional[dict]:
    for source, pattern in _ATS_PATTERNS:
        m = pattern.search(text)
        if m:
            return {"source": source, "slug": m.group(1).lower()}
    m = _WORKDAY_RE.search(text)
    if m:
        subdomain, wd, site = m.groups()
        host = f"{subdomain.lower()}.{wd.lower()}.myworkdayjobs.com"
        return {
            "source": "workday",
            "host": host,
            "tenant": subdomain.lower(),
            "site": site,
        }
    return None


def detect(url: str) -> Optional[dict]:
    """Detect the ATS for a URL. Checks the URL itself first, then fetches
    the page and searches its HTML."""
    # Normalize bare domains to https://
    if not urlparse(url).scheme:
        url = "https://" + url

    direct = _match_ats(url)
    if direct:
        return direct

    try:
        r = requests.get(url, headers={"User-Agent": _UA}, timeout=15, allow_redirects=True)
        r.raise_for_status()
    except requests.RequestException:
        return None

    hit = _match_ats(r.url) or _match_ats(r.text)
    return hit
