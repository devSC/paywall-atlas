#!/usr/bin/env python3
"""Read public PaywallPro list pages politely; stop on access restrictions."""

import argparse
import datetime as dt
import json
import pathlib
import random
import subprocess
import time


def request(page: int, resolve: str | None) -> dict:
    payload = {
        "mode": "fall",
        "page": page,
        "limit": 12,
        "region_code": 1102,
        "sort": {"type": "recent_update_date", "order": "desc"},
    }
    cmd = [
        "curl", "--silent", "--show-error", "--fail", "--max-time", "40",
        "--retry", "3", "--retry-all-errors", "--retry-delay", "3",
        "--noproxy", "*", "--user-agent", "paywall-atlas-refresh/1.0",
    ]
    if resolve:
        cmd += ["--resolve", f"www.paywallpro.app:443:{resolve}"]
    cmd += [
        "https://www.paywallpro.app/api/app-list",
        "-H", "Content-Type: application/json", "--data-binary", "@-",
    ]
    result = subprocess.run(
        cmd, input=json.dumps(payload), text=True, capture_output=True, check=False
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip())
    return json.loads(result.stdout)


def ranged_sleep(rng: random.Random, minimum: float, maximum: float, label: str) -> None:
    seconds = rng.uniform(minimum, maximum)
    if seconds <= 0:
        return
    print(json.dumps({"event": label, "seconds": round(seconds, 2)}), flush=True)
    time.sleep(seconds)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", required=True)
    parser.add_argument("--resolve")
    parser.add_argument("--year", type=int, default=2026)
    parser.add_argument("--delay-min", type=float, default=0.35)
    parser.add_argument("--delay-max", type=float, default=0.35)
    parser.add_argument("--break-every-min", type=int, default=0)
    parser.add_argument("--break-every-max", type=int, default=0)
    parser.add_argument("--break-min", type=float, default=0)
    parser.add_argument("--break-max", type=float, default=0)
    parser.add_argument("--seed", type=int)
    args = parser.parse_args()
    if not 2000 <= args.year <= 2100:
        parser.error("--year must be between 2000 and 2100")
    for low, high, name in [
        (args.delay_min, args.delay_max, "delay"),
        (args.break_min, args.break_max, "break"),
    ]:
        if low < 0 or high < low:
            parser.error(f"invalid {name} range")
    if args.break_every_min < 0 or args.break_every_max < args.break_every_min:
        parser.error("invalid break-every range")
    return args


def main() -> None:
    args = parse_args()
    cache = pathlib.Path(args.cache)
    cache.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)
    paced_breaks = args.break_every_min > 0
    next_break = (
        rng.randint(args.break_every_min, args.break_every_max) if paced_breaks else None
    )
    fetched_since_break = 0
    report = {
        "year": args.year,
        "date_field": "recent_capture_update",
        "region_code": 1102,
        "started_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "pages": 0,
        "status": "partial",
        "stop_reason": None,
        "reported_count": None,
        "pacing": {
            "delay_seconds": [args.delay_min, args.delay_max],
            "break_every_pages": [args.break_every_min, args.break_every_max],
            "break_seconds": [args.break_min, args.break_max],
            "transparent_user_agent": "paywall-atlas-refresh/1.0",
        },
    }
    rows: list[dict] = []
    seen: set[str] = set()
    page = 1
    try:
        while True:
            file = cache / f"page-{page:04}.json"
            from_cache = file.exists()
            if from_cache:
                result = json.loads(file.read_text())
            else:
                result = request(page, args.resolve)
                file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
                fetched_since_break += 1
                ranged_sleep(rng, args.delay_min, args.delay_max, "page_delay")
                if next_break is not None and fetched_since_break >= next_break:
                    ranged_sleep(rng, args.break_min, args.break_max, "session_break")
                    fetched_since_break = 0
                    next_break = rng.randint(args.break_every_min, args.break_every_max)
            if str(result.get("code")) != "200":
                report.update(
                    stop_reason=f"API {result.get('code')}: {result.get('msg')}",
                    blocked_page=page,
                )
                break
            body = result.get("data") or {}
            batch = body.get("rows")
            count = body.get("count")
            if not isinstance(batch, list):
                raise RuntimeError("Invalid rows shape")
            if report["reported_count"] is None:
                report["reported_count"] = count
            elif count != report["reported_count"]:
                report["count_changed"] = True
            novel = 0
            for row in batch:
                key = str(row.get("info_id") or row.get("app_id"))
                if key not in seen:
                    seen.add(key)
                    rows.append(row)
                    novel += 1
            report["pages"] = page
            dates = [
                row.get("recent_capture_update")
                for row in batch
                if row.get("recent_capture_update")
            ]
            print(
                json.dumps(
                    {
                        "page": page,
                        "rows": len(batch),
                        "unique_total": len(rows),
                        "oldest": min(dates) if dates else None,
                        "source": "cache" if from_cache else "network",
                    }
                ),
                flush=True,
            )
            if not batch or (isinstance(count, int) and page * 12 >= count):
                report["status"] = (
                    "complete"
                    if len(rows) == count and not report.get("count_changed")
                    else "partial"
                )
                report["stop_reason"] = "Public list exhausted"
                break
            if novel == 0:
                report["stop_reason"] = "Repeated page; pagination did not advance"
                break
            page += 1
    except (RuntimeError, ValueError, OSError) as error:
        report["stop_reason"] = str(error)
    report["finished_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    report["unique_rows"] = len(rows)
    selected = [
        row for row in rows
        if str(row.get("recent_capture_update", "")).startswith(f"{args.year}-")
    ]
    report["selected_rows"] = len(selected)
    report["unknown_dates"] = sum(not row.get("recent_capture_update") for row in rows)
    (cache / "rows.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2))
    (cache / "selected.json").write_text(json.dumps(selected, ensure_ascii=False, indent=2))
    (cache / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps(report, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
