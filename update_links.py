#!/usr/bin/env python3
"""user_links.json を更新するスクリプト。環境変数から引数を受け取る。

環境変数:
  ACTION    : add | delete
  TASK_NAME : タスク名
  LABEL     : リンクラベル（add時）
  URL       : リンクURL（add時）
  LINK_ID   : リンクID（delete時、数値文字列）
"""

import json
import os
import time
from pathlib import Path

LINKS_FILE = Path("user_links.json")


def load():
    if LINKS_FILE.exists():
        return json.loads(LINKS_FILE.read_text(encoding="utf-8"))
    return {}


def save(data):
    LINKS_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def main():
    action = os.environ.get("ACTION", "").strip()
    task_name = os.environ.get("TASK_NAME", "").strip()

    if not action or not task_name:
        raise SystemExit("ERROR: ACTION and TASK_NAME are required")

    data = load()

    if action == "add":
        label = os.environ.get("LABEL", "アウトプット").strip() or "アウトプット"
        url = os.environ.get("URL", "").strip()
        if not url:
            raise SystemExit("ERROR: URL is required for add action")
        if task_name not in data:
            data[task_name] = []
        data[task_name].append(
            {"label": label, "url": url, "id": int(time.time() * 1000)}
        )
        print(f"Added link '{label}' -> {url} for '{task_name}'")

    elif action == "delete":
        link_id_str = os.environ.get("LINK_ID", "").strip()
        if not link_id_str:
            raise SystemExit("ERROR: LINK_ID is required for delete action")
        link_id = int(link_id_str)
        if task_name in data:
            before = len(data[task_name])
            data[task_name] = [
                lk for lk in data[task_name] if lk.get("id") != link_id
            ]
            if not data[task_name]:
                del data[task_name]
            after = len(data.get(task_name, []))
            print(f"Deleted id={link_id} from '{task_name}' ({before}->{after})")
        else:
            print(f"Task '{task_name}' not found in links (no-op)")

    else:
        raise SystemExit(f"ERROR: Unknown action '{action}'")

    save(data)


if __name__ == "__main__":
    main()
