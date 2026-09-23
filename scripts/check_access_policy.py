#!/usr/bin/env python3
"""Guard the lightweight time-based access gate contract."""

from pathlib import Path


html = (Path(__file__).resolve().parents[1] / "index.html").read_text(encoding="utf-8")

assert 'id="access-gate"' in html
assert 'id="app-shell" hidden' in html
assert "timeZone:'Asia/Singapore'" in html
assert "crypto.subtle.digest('SHA-256'" in html
assert "script.src='data.js'" in html
assert '<script src="data.js"></script>' not in html
assert "112358" not in html, "the password prefix must not appear as plaintext"
print("PASS: access gate, SHA-256 check, hourly scope, and deferred data loading are present")
