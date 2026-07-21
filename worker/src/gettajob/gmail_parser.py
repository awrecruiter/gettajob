"""Gmail job-alert parser — IMAP fetch, URL extract, ATS detection.

Given a Gmail account + app password, pulls recent messages from known
job-alert senders (LinkedIn / Indeed / ZipRecruiter / recruiter mail),
extracts job-adjacent URLs, and runs each through the ATS detector so
you get back a config-ready list of employers to add.
"""
from __future__ import annotations

import email
import imaplib
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from email.message import Message
from typing import Iterable, Optional

from gettajob.detector import detect as detect_ats

IMAP_HOST = "imap.gmail.com"

# Grab http(s) URLs, stopping at whitespace / common quote/close chars.
_URL_RE = re.compile(r"https?://[^\s<>\"'\]\)}]+", re.I)

# Only surface links pointing to job-adjacent hosts — job-alert emails
# are full of unrelated URLs (unsubscribe, privacy policy, tracking pixels).
_JOB_HOSTS = re.compile(
    r"(greenhouse\.io|lever\.co|ashbyhq\.com|myworkdayjobs\.com|"
    r"jobs\.[a-z0-9-]+\.com|careers\.[a-z0-9-]+\.com)",
    re.I,
)

DEFAULT_SENDERS = [
    "jobs-noreply@linkedin.com",
    "jobalerts-noreply@linkedin.com",
    "job-alerts@linkedin.com",
    "alert@indeed.com",
    "noreply@indeed.com",
    "notify@ziprecruiter.com",
    "no-reply@ziprecruiter.com",
]


@dataclass
class DiscoveredAlert:
    from_addr: str
    subject: str
    date: str
    urls: list[str] = field(default_factory=list)
    detections: list[dict] = field(default_factory=list)


def _decode_part(part: Message) -> str:
    try:
        payload = part.get_payload(decode=True)
        if not payload:
            return ""
        charset = part.get_content_charset() or "utf-8"
        return payload.decode(charset, errors="replace")
    except (UnicodeDecodeError, LookupError):
        return ""


def _extract_urls(msg: Message) -> list[str]:
    body: list[str] = []
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() in ("text/plain", "text/html"):
                body.append(_decode_part(part))
    else:
        body.append(_decode_part(msg))
    text = "\n".join(body)
    urls = _URL_RE.findall(text)
    return [u for u in urls if _JOB_HOSTS.search(u)]


def _unique_detections(urls: list[str]) -> list[dict]:
    """Return the ordered set of unique ATS detections for a URL list."""
    seen: set[tuple] = set()
    out: list[dict] = []
    for u in urls:
        d = detect_ats(u)
        if not d:
            continue
        key = tuple(sorted(d.items()))
        if key in seen:
            continue
        seen.add(key)
        out.append(d)
    return out


def scan_inbox(
    user: str,
    password: str,
    since_days: int = 7,
    senders: Optional[list[str]] = None,
) -> Iterable[DiscoveredAlert]:
    """Yield DiscoveredAlert per matching Gmail message."""
    senders = senders or DEFAULT_SENDERS
    since = (datetime.now() - timedelta(days=since_days)).strftime("%d-%b-%Y")

    m = imaplib.IMAP4_SSL(IMAP_HOST)
    m.login(user, password)
    try:
        m.select("INBOX")
        for sender in senders:
            typ, data = m.search(None, f'(FROM "{sender}" SINCE {since})')
            if typ != "OK":
                continue
            ids = data[0].split()
            for uid in ids:
                typ, msg_data = m.fetch(uid, "(RFC822)")
                if typ != "OK" or not msg_data or not msg_data[0]:
                    continue
                raw = msg_data[0][1]
                msg = email.message_from_bytes(raw)
                urls = _extract_urls(msg)
                yield DiscoveredAlert(
                    from_addr=msg.get("From", ""),
                    subject=msg.get("Subject", ""),
                    date=msg.get("Date", ""),
                    urls=urls,
                    detections=_unique_detections(urls),
                )
    finally:
        try:
            m.logout()
        except Exception:
            pass
