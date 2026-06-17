#!/usr/bin/env python3
"""tasks.jsonをHTMLに埋め込んでindex.htmlを出力する。

優先順位:
  1. HTML内に TASKS_PLACEHOLDER があればそれを置換
  2. なければ既存の `var T = [...];` を正規表現で置換
"""

import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

HTML_SRC = "業務ダッシュボードv7.html"
TASKS_JSON = "tasks.json"
USER_LINKS_JSON = "user_links.json"
WFH_JSON = "wfh_reports.json"
HTML_OUT = "index.html"
PLACEHOLDER = "TASKS_PLACEHOLDER"
VAR_T_PATTERN = re.compile(r"var\s+T\s*=\s*\[.*?\];", re.DOTALL)
VAR_UL_PATTERN = re.compile(r"var\s+UL\s*=\s*\{.*?\};", re.DOTALL)
VAR_WFH_PATTERN = re.compile(r"var\s+WFH\s*=\s*\[.*?\];", re.DOTALL)
BUILD_TS_PLACEHOLDER = '"BUILD_TIMESTAMP"'
SYNC_TOKEN_PLACEHOLDER = "SYNC_TOKEN_PLACEHOLDER"
USER_LINKS_PLACEHOLDER = "USER_LINKS_PLACEHOLDER"
WFH_PLACEHOLDER = "WFH_REPORTS_PLACEHOLDER"


def main():
    html_path = Path(HTML_SRC)
    tasks_path = Path(TASKS_JSON)

    if not html_path.exists():
        sys.exit(f"ERROR: {HTML_SRC} not found in current directory")
    if not tasks_path.exists():
        sys.exit(f"ERROR: {TASKS_JSON} not found. Run fetch_notion.py first.")

    html = html_path.read_text(encoding="utf-8")
    with tasks_path.open("r", encoding="utf-8") as f:
        tasks = json.load(f)
    tasks_json = json.dumps(tasks, ensure_ascii=False)

    if PLACEHOLDER in html:
        html_out = html.replace(PLACEHOLDER, tasks_json)
        mode = "placeholder"
    else:
        if not VAR_T_PATTERN.search(html):
            sys.exit(
                f"ERROR: neither '{PLACEHOLDER}' nor 'var T = [...];' "
                "found in HTML"
            )
        html_out = VAR_T_PATTERN.sub(
            "var T = " + tasks_json + ";", html, count=1
        )
        mode = "var T pattern"

    # Inject user_links.json as UL variable
    user_links_path = Path(USER_LINKS_JSON)
    user_links = {}
    if user_links_path.exists():
        with user_links_path.open("r", encoding="utf-8") as f:
            user_links = json.load(f)
    user_links_json = json.dumps(user_links, ensure_ascii=False)
    if USER_LINKS_PLACEHOLDER in html_out:
        html_out = html_out.replace(USER_LINKS_PLACEHOLDER, user_links_json)
    elif VAR_UL_PATTERN.search(html_out):
        html_out = VAR_UL_PATTERN.sub(
            "var UL = " + user_links_json + ";", html_out, count=1
        )

    # Inject wfh_reports.json as WFH variable
    wfh_path = Path(WFH_JSON)
    wfh = []
    if wfh_path.exists():
        with wfh_path.open("r", encoding="utf-8") as f:
            wfh = json.load(f)
    wfh_json = json.dumps(wfh, ensure_ascii=False)
    if WFH_PLACEHOLDER in html_out:
        html_out = html_out.replace(WFH_PLACEHOLDER, wfh_json)
    elif VAR_WFH_PATTERN.search(html_out):
        html_out = VAR_WFH_PATTERN.sub(
            "var WFH = " + wfh_json + ";", html_out, count=1
        )

    jst = timezone(timedelta(hours=9))
    build_ts = datetime.now(jst).strftime("%Y-%m-%d %H:%M JST")
    html_out = html_out.replace(BUILD_TS_PLACEHOLDER, f'"{build_ts}"')

    sync_token = os.environ.get("SYNC_TOKEN", "")
    html_out = html_out.replace(SYNC_TOKEN_PLACEHOLDER, sync_token)

    Path(HTML_OUT).write_text(html_out, encoding="utf-8")
    print(f"Wrote {HTML_OUT} ({len(tasks)} tasks, {len(user_links)} linked tasks, {len(wfh)} wfh days, replaced via {mode}, built at {build_ts})")


if __name__ == "__main__":
    main()
