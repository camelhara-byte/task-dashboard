#!/usr/bin/env python3
"""wfh_reports.json（在宅報告）を更新するスクリプト。環境変数から引数を受け取る。

環境変数:
  ACTION  : save | delete
  DATE    : 対象日（YYYY-MM-DD）
  PAYLOAD : save時のJSON文字列 {"blocks":[...], "end":"17:00"}

データ形式（wfh_reports.json）:
  [ {"date":"2026-06-17", "blocks":[{"start":"09:00","task":"...","memo":"..."},
                                     {"start":"12:00","brk":true}], "end":"17:00"}, ... ]
"""

import json
import os
import sys
from pathlib import Path

WFH_FILE = Path("wfh_reports.json")


def load():
    if WFH_FILE.exists():
        try:
            data = json.loads(WFH_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass
    return []


def save(data):
    # 日付の新しい順に並べて保存
    data.sort(key=lambda d: d.get("date", ""), reverse=True)
    WFH_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def sanitize_blocks(blocks):
    """想定外のキーを落として最小限のスキーマに整える。"""
    clean = []
    if not isinstance(blocks, list):
        return clean
    for b in blocks:
        if not isinstance(b, dict):
            continue
        start = str(b.get("start", "")).strip()
        if b.get("brk"):
            clean.append({"start": start, "brk": True})
        else:
            clean.append({
                "start": start,
                "task": str(b.get("task", "")).strip(),
                "memo": str(b.get("memo", "")).strip(),
            })
    return clean


def main():
    action = os.environ.get("ACTION", "").strip()
    date = os.environ.get("DATE", "").strip()

    if not action or not date:
        raise SystemExit("ERROR: ACTION and DATE are required")

    data = load()
    # 既存の同一日エントリを除去
    data = [d for d in data if d.get("date") != date]

    if action == "save":
        payload_raw = os.environ.get("PAYLOAD", "").strip()
        if not payload_raw:
            raise SystemExit("ERROR: PAYLOAD is required for save action")
        try:
            payload = json.loads(payload_raw)
        except json.JSONDecodeError as e:
            raise SystemExit(f"ERROR: invalid PAYLOAD JSON: {e}")
        entry = {
            "date": date,
            "blocks": sanitize_blocks(payload.get("blocks", [])),
            "end": str(payload.get("end", "")).strip(),
        }
        data.append(entry)
        print(f"Saved WFH report for {date} ({len(entry['blocks'])} blocks)")

    elif action == "delete":
        print(f"Deleted WFH report for {date}")

    else:
        raise SystemExit(f"ERROR: Unknown action '{action}'")

    save(data)


if __name__ == "__main__":
    main()
