"""Extract required years of experience from a job description.

Looks for patterns like "5+ years of experience" or "minimum 3 years"
and returns the minimum requirement mentioned — that's the floor a
candidate has to clear. Multiple mentions ("5+ years engineering,
10+ years leadership preferred") resolve to the smaller value so the
filter surfaces roles where the base requirement is met.
"""
from __future__ import annotations

import re
from typing import Optional

# Match either:
#   "5+ years of ... experience" — "X years [1-3 filler words] experience"
#   "minimum of 3 years"
#   "at least 7 years"
_YEARS_PATTERNS = [
    # "3-5 years" / "3 to 5 years" — capture the LOW end as the floor.
    re.compile(
        r"\b(\d{1,2})\s*(?:-|–|—|to)\s*\d{1,2}\s*years?\s*(?:of\s+)?(?:\w+\s+){0,3}?experience\b",
        re.I,
    ),
    re.compile(
        r"\b(\d{1,2})\s*\+?\s*years?\s*(?:of\s+)?(?:\w+\s+){0,3}?experience\b",
        re.I,
    ),
    re.compile(r"\bminimum\s+(?:of\s+)?(\d{1,2})\s*\+?\s*years?", re.I),
    re.compile(r"\bat\s+least\s+(\d{1,2})\s*\+?\s*years?", re.I),
]


def extract_years_required(text: Optional[str]) -> Optional[int]:
    """Return the minimum years-of-experience mentioned as a requirement.

    Returns None if no candidate patterns match. Values above 30 are
    treated as noise (some JDs reference decade-long history in prose).
    """
    if not text:
        return None
    values: list[int] = []
    for pat in _YEARS_PATTERNS:
        for m in pat.finditer(text):
            try:
                n = int(m.group(1))
            except (ValueError, IndexError):
                continue
            if 0 < n <= 30:
                values.append(n)
    return min(values) if values else None
