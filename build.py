#!/usr/bin/env python3
"""tasks.jsonをHTMLに埋め込んでindex.htmlを出力する。

優先順位:
  1. HTML内に TASKS_PLACEHOLDER があればそれを置換
  2. なければ既存の `var T = [...];` を正規表現で置換
"""

import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

HTML_SRC = "業務ダッシュボードv7.html"
TASKS_JSON = "tasks.json"
HTML_OUT = "index.html"
PLACEHOLDER = "TASKS_PLACEHOLDER"
VAR_T_PATTERN = re.compile(r"var\s+T\s*=\s*\[.*?\];", re.DOTALL)
BUILD_TS_PLACEHOLDER = '"BUILD_TIMESTAMP"'


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

    jst = timezone(timedelta(hours=9))
    build_ts = datetime.now(jst).strftime("%Y-%m-%d %H:%M JST")
    html_out = html_out.replace(BUILD_TS_PLACEHOLDER, f'"{build_ts}"')

    Path(HTML_OUT).write_text(html_out, encoding="utf-8")
    print(f"Wrote {HTML_OUT} ({len(tasks)} tasks, replaced via {mode}, built at {build_ts})")


if __name__ == "__main__":
    main()
