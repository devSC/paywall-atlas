#!/usr/bin/env python3
"""Interactive, polite refresh wizard for WALL / ATLAS."""

import argparse
import datetime as dt
import json
import pathlib
import subprocess
import sys
from zoneinfo import ZoneInfo


ROOT = pathlib.Path(__file__).resolve().parents[1]
RESOURCE_PATHS = [
    "data.js",
    "manifest.json",
    "reports/collection.json",
    "reports/integrity.json",
    "reports/link-checks.json",
    "reports/undated-records.json",
]
PACES = {
    "gentle": {
        "label": "温和（推荐，约 15–25 分钟）",
        "args": [
            "--delay-min", "1.2", "--delay-max", "2.8",
            "--break-every-min", "24", "--break-every-max", "36",
            "--break-min", "7", "--break-max", "15",
        ],
    },
    "balanced": {
        "label": "均衡（约 8–15 分钟）",
        "args": [
            "--delay-min", "0.6", "--delay-max", "1.4",
            "--break-every-min", "40", "--break-every-max", "60",
            "--break-min", "3", "--break-max", "8",
        ],
    },
    "fast": {
        "label": "快速（固定 0.35 秒，不模拟浏览节奏）",
        "args": ["--delay-min", "0.35", "--delay-max", "0.35"],
    },
}


def ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{prompt}{suffix}: ").strip()
    return value or default


def confirm(prompt: str, default: bool = False) -> bool:
    suffix = "Y/n" if default else "y/N"
    value = input(f"{prompt} [{suffix}]: ").strip().lower()
    if not value:
        return default
    return value in {"y", "yes", "是"}


def choose_pace() -> str:
    print("\n抓取节奏：")
    keys = list(PACES)
    for index, key in enumerate(keys, 1):
        print(f"  {index}. {PACES[key]['label']}")
    value = ask("请选择", "1")
    if value not in {"1", "2", "3"}:
        raise SystemExit("无效的节奏选项")
    return keys[int(value) - 1]


def run(command: list[str]) -> None:
    print("\n$ " + " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", action="store_true", help="只显示默认计划，不执行")
    parser.add_argument("--year", type=int)
    parser.add_argument("--cache", type=pathlib.Path)
    parser.add_argument("--pace", choices=PACES)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    now = dt.datetime.now(ZoneInfo("Asia/Singapore"))
    default_year = args.year or now.year
    default_cache = args.cache or pathlib.Path(
        f"/tmp/paywallpro-{default_year}-{now:%Y%m%d-%H%M%S}"
    )
    if args.plan:
        pace = args.pace or "gentle"
        print(json.dumps(
            {"year": default_year, "cache": str(default_cache), "pace": pace},
            ensure_ascii=False,
            indent=2,
        ))
        return 0

    print("WALL / ATLAS 资源更新向导")
    print("读取公开列表；不伪装身份、不绕过验证码或权限控制。")
    year = int(ask("目标年份", str(default_year)))
    cache = pathlib.Path(ask("缓存目录", str(default_cache))).expanduser()
    pace = args.pace or choose_pace()
    resolve = ask("可选：主站真实 IP（普通网络请留空）")
    print("\n更新计划")
    print(f"  年份：{year}")
    print(f"  缓存：{cache}")
    print(f"  节奏：{PACES[pace]['label']}")
    print("  媒体：只保存 URL，不下载图片或视频")
    if not confirm("开始抓取"):
        print("已取消，没有修改仓库。")
        return 0

    collect = [
        sys.executable, "scripts/collect.py", "--cache", str(cache),
        "--year", str(year), *PACES[pace]["args"],
    ]
    if resolve:
        collect += ["--resolve", resolve]
    run(collect)
    report = json.loads((cache / "report.json").read_text())
    print(
        f"\n抓取结果：{report['status']}，来源 {report['unique_rows']} 条，"
        f"{year} 年 {report['selected_rows']} 条。"
    )
    if report["status"] != "complete":
        print(f"未发布部分结果：{report['stop_reason']}")
        print(f"修复连接后使用同一缓存目录继续：{cache}")
        return 2
    if not confirm("生成并覆盖网页资源数据"):
        print(f"抓取缓存已保留：{cache}")
        return 0

    run([sys.executable, "scripts/build_data.py", "--cache", str(cache)])
    run([sys.executable, "scripts/audit_collection.py", "--cache", str(cache)])
    if confirm("检查代表截图和全部视频链接（耗时较长）", default=True):
        run([
            sys.executable, "scripts/check_links.py", "--cache", str(cache),
            "--output", "reports/link-checks.json",
        ])
    else:
        print("已跳过链接检查；reports/link-checks.json 仍是上次结果。")
    run([sys.executable, "scripts/check_access_policy.py"])
    run([sys.executable, "scripts/check_media_policy.py"])
    run(["git", "diff", "--stat", "--", *RESOURCE_PATHS])

    if not confirm("提交并推送到个人仓库，触发 Pages 部署"):
        print("数据已在本地生成，尚未提交。")
        return 0
    run(["git", "add", "--", *RESOURCE_PATHS])
    staged = subprocess.run(
        ["git", "diff", "--cached", "--quiet"], cwd=ROOT, check=False
    )
    if staged.returncode == 0:
        print("资源没有变化，无需提交。")
        return 0
    message = ask("提交信息", f"Refresh {year} paywall resources")
    run(["git", "commit", "-m", message])
    run(["git", "push", "origin", "main"])
    print("\n更新完成：https://devsc.github.io/paywall-atlas/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
