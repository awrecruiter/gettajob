"""Shared HTML utilities for connectors that receive rich text bodies."""
import re
from html import unescape
from html.parser import HTMLParser
from typing import Optional

# Tags that should force a newline in the plain-text output so paragraphs
# and list items don't collapse into one wall of text.
_BLOCK_TAGS = {
    "p", "div", "br", "li", "ul", "ol", "tr", "hr", "section",
    "article", "header", "footer", "blockquote", "pre",
    "h1", "h2", "h3", "h4", "h5", "h6",
}

_MULTI_NEWLINE = re.compile(r"\n{3,}")
_TRAILING_SPACE = re.compile(r"[ \t]+\n")


class _Stripper(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in _BLOCK_TAGS:
            self.parts.append("\n")


def strip_html(html: Optional[str]) -> Optional[str]:
    """Return the visible text of an HTML fragment, preserving paragraph
    breaks at block-level tag boundaries.

    Unescapes before parsing so double-encoded input (e.g. Greenhouse's
    &lt;div&gt;-wrapped content) is stripped cleanly instead of surviving
    as raw tag text.
    """
    if not html:
        return html
    s = _Stripper()
    s.feed(unescape(html))
    text = "".join(s.parts)
    text = _TRAILING_SPACE.sub("\n", text)
    text = _MULTI_NEWLINE.sub("\n\n", text)
    return text.strip()
