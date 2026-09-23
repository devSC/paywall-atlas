#!/usr/bin/env python3
"""Guard gallery pagination and remote-media rendering policies."""

import json
import math
import pathlib
import re


root = pathlib.Path(__file__).resolve().parents[1]
html = (root / "index.html").read_text(encoding="utf-8")
data = (root / "data.js").read_text(encoding="utf-8")

match = re.search(r"const pageSize=(\d+)", html)
assert match, "index.html must declare pageSize"
page_size = int(match.group(1))
assert page_size == 100, f"expected 100 records per page, got {page_size}"

meta_text = data.split(";\n", 1)[0].removeprefix("window.PAYWALL_META = ")
meta = json.loads(meta_text)
expected_pages = math.ceil(meta["total_apps"] / page_size)
assert expected_pages == 15, f"expected 15 pages for current data, got {expected_pages}"
assert 'loading="lazy"' in html, "remote screenshots must remain lazily loaded"
assert 'preload="none"' in html, "videos must not preload across 100 rows"
print(
    f"PASS: {page_size} records per page, {expected_pages} current pages, "
    "lazy images, and non-preloaded videos"
)
