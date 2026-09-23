#!/usr/bin/env python3
"""Offline regression checks for the refresh workflow."""

import json
import pathlib
import subprocess
import sys
import tempfile


ROOT = pathlib.Path(__file__).resolve().parents[1]


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=True)


with tempfile.TemporaryDirectory() as temporary:
    cache = pathlib.Path(temporary) / "cache"
    cache.mkdir()
    rows = [
        {
            "info_id": index,
            "app_id": 1000 + index,
            "app_name": f"Fixture {index}",
            "recent_capture_update": "2027-01-02" if index == 1 else "2026-12-31",
            "captures": [],
            "onboarding_url": "",
        }
        for index in range(1, 14)
    ]
    for page, batch in [(1, rows)]:
        (cache / f"page-{page:04}.json").write_text(json.dumps({
            "code": 200,
            "data": {"count": 13, "rows": batch},
        }))
    result = run([
        sys.executable, "scripts/collect.py", "--cache", str(cache),
        "--year", "2027", "--delay-min", "99", "--delay-max", "99",
        "--break-every-min", "1", "--break-every-max", "1",
        "--break-min", "99", "--break-max", "99",
    ])
    report = json.loads((cache / "report.json").read_text())
    assert report["status"] == "complete"
    assert report["unique_rows"] == 13
    assert report["selected_rows"] == 1
    assert '"source": "cache"' in result.stdout
    assert '"event": "page_delay"' not in result.stdout

    legacy_cache = pathlib.Path(temporary) / "legacy-cache"
    legacy_cache.mkdir()
    (legacy_cache / "page-0001.json").write_text(json.dumps({
        "code": 200,
        "data": {"count": 13, "rows": rows[:12]},
    }))
    mismatch = subprocess.run(
        [sys.executable, "scripts/collect.py", "--cache", str(legacy_cache)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert mismatch.returncode != 0
    assert "existing cache uses 12 records per page" in mismatch.stderr

    link_report = pathlib.Path(temporary) / "links.json"
    run([
        sys.executable, "scripts/check_links.py", "--cache", str(cache),
        "--output", str(link_report),
    ])
    checked = json.loads(link_report.read_text())
    assert checked["apps"] == 1
    assert checked["links"] == 0

    cancelled_cache = pathlib.Path(temporary) / "cancelled"
    cancelled = subprocess.run(
        [sys.executable, "scripts/refresh.py"],
        cwd=ROOT,
        input=f"2027\n{cancelled_cache}\n1\n\nn\n",
        text=True,
        capture_output=True,
        check=True,
    )
    assert "已取消，没有修改仓库" in cancelled.stdout
    assert not cancelled_cache.exists()

plan = run([
    sys.executable, "scripts/refresh.py", "--plan", "--year", "2027",
    "--cache", "/tmp/example-refresh", "--pace", "gentle",
])
assert json.loads(plan.stdout) == {
    "year": 2027,
    "cache": "/tmp/example-refresh",
    "pace": "gentle",
}
print("PASS: cached resume skips delays, year filtering is dynamic, and wizard planning is deterministic")
