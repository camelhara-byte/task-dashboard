#!/usr/bin/env python3
"""tasks.jsonをHTMLに埋め込んでindex.htmlを出力する。

優先順位:
  1. HTML内に TASKS_PLACEHOLDER があればそれを置換
  2. なければ既存の `var T = [...];` を正規表現で置換
"""

import json
import re
import sys
from pathlib import Path

HTML_SRC = "業務ダッシュボードv7.html"
TASKS_JSON = "tasks.json"
HTML_OUT = "index.html"
PLACEHOLDER = "TASKS_PLACEHOLDER"
VAR_T_PATTERN = re.compile(r"var\s+T\s*=\s*\[.*?\];", re.DOTALL)


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

    Path(HTML_OUT).write_text(html_out, encoding="utf-8")
    print(f"Wrote {HTML_OUT} ({len(tasks)} tasks, replaced via {mode})")


if __name__ == "__main__":
    main()
