#!/usr/bin/env python3
"""Guard the referrer policy required by the remote media CDN."""

from html.parser import HTMLParser
from pathlib import Path


class ReferrerPolicyParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.policies: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "meta":
            return
        values = dict(attrs)
        if values.get("name", "").lower() == "referrer" and values.get("content"):
            self.policies.append(values["content"].lower())


root = Path(__file__).resolve().parents[1]
parser = ReferrerPolicyParser()
parser.feed((root / "index.html").read_text(encoding="utf-8"))

assert parser.policies == ["no-referrer"], (
    "index.html must declare exactly one no-referrer policy; "
    "the media CDN rejects GitHub Pages Referer headers"
)
print("PASS: index.html declares the required no-referrer media policy")
