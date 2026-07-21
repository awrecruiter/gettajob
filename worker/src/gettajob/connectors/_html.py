"""Shared HTML utilities for connectors that receive rich text bodies."""
from html import unescape
from html.parser import HTMLParser
from typing import Optional


class _Stripper(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def strip_html(html: Optional[str]) -> Optional[str]:
    """Return the visible text of an HTML fragment.

    Unescapes before parsing so double-encoded input (e.g. Greenhouse's
    &lt;div&gt;-wrapped content) is stripped cleanly instead of surviving
    as raw tag text.
    """
    if not html:
        return html
    s = _Stripper()
    s.feed(unescape(html))
    return " ".join(s.parts).strip()
