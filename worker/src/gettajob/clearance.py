"""Regex extractor for `clearance_required` from job descriptions.

Real defense JDs vary in how they list clearances — sometimes prose
("must possess an active TS/SCI clearance"), sometimes bulleted
("Secret clearance", "TS/SCI clearance with polygraph"), sometimes
soft ("eligible for a security clearance", "ability to obtain").

Strategy: find each mention of the word "clearance", inspect the
surrounding window, and classify it as required (any specific level
word nearby, no opt-out language) or not.
"""
from __future__ import annotations

import re
from typing import Optional

# Clearance-level indicators. Matching any of these in the window near
# "clearance" is a strong signal the JD is talking about a specific bar.
_LEVEL_WORDS = re.compile(
    r"\b(top\s*secret|ts\s*/?\s*sci|ts[- ]sci|secret|public\s+trust|"
    r"full[\s-]*scope\s+poly(?:graph)?|q\s+clearance|l\s+clearance)\b",
    re.I,
)

# Soft-context words — presence within the window turns a level mention
# into "candidates without a clearance can still apply."
_SOFT_WORDS = re.compile(
    r"\b(ability\s+to\s+obtain|able\s+to\s+obtain|willing\s+to\s+obtain|"
    r"willingness\s+to\s+obtain|eligibility|eligible|"
    r"preferred|nice[\s-]+to[\s-]+have|would\s+be\s+a\s+plus|"
    r"is\s+not\s+required|does\s+not\s+require|no\s+clearance\s+required|"
    r"ability\s+to\s+get)\b",
    re.I,
)

# A window around each "clearance" mention. Wide enough to catch a
# sentence, narrow enough not to bleed into neighboring bullets.
_WINDOW = 140


def extract_clearance_required(text: Optional[str]) -> Optional[bool]:
    """Return True when the JD requires an existing clearance.

    Returns None if unknown or every mention is soft-context. Never
    returns False — that judgment is left to the AI scorer.
    """
    if not text:
        return None
    lower = text.lower()
    if "clearance" not in lower:
        return None
    found_hard = False
    for m in re.finditer(r"clearance", lower):
        start = max(0, m.start() - _WINDOW)
        end = min(len(text), m.end() + _WINDOW)
        window = text[start:end]
        if not _LEVEL_WORDS.search(window):
            continue
        if _SOFT_WORDS.search(window):
            continue
        found_hard = True
        break
    return True if found_hard else None
