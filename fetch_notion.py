#!/usr/bin/env python3
"""Notion APIからタスクデータを取得してtasks.jsonを出力する。

環境変数 NOTION_API_KEY を使用。

出力スキーマ (tasks_v6.json と同等 + url 追加):
  name, category, status, size, priority, updateDate, month, subtasks[], links[], url
"""

import json
import os
import sys
import time
from urllib import request as urlrequest
from urllib import error as urlerror

DATABASE_ID = "31eb5de8e03680e68d8bf4d5f38309c1"
NOTION_VERSION = "2022-06-28"
API_BASE = "https://api.notion.com/v1"

CATEGORIES = [
    "マーケティング",
    "マニュアル・教育",
    "助成金・申請",
    "院内オペレーション",
    "労務・人事",
    "システム・DX",
    "その他",
]

# 順序が重要: 上から評価して最初にマッチしたカテゴリに分類
CATEGORY_KEYWORDS = [
    ("助成金・申請", ["助成金", "補助金", "企業型DC", "DC申請"]),
    ("マニュアル・教育", ["マニュアル", "セミナー", "修了証", "研修", "教育"]),
    ("労務・人事", ["勤怠", "就業規則", "入社", "適性検査", "ジョブカン",
                    "ジョブメドレー", "求人", "リクルート", "スタッフ表",
                    "労務", "人事"]),
    ("院内オペレーション", ["レセプト", "自動レジ", "レジ導入", "同意書",
                            "承諾書", "予約システム", "オペスケ",
                            "デントネット", "修理伝票", "マネジメントアプリ",
                            "院内"]),
    ("マーケティング", ["HP", "Web", "SNS", "ロゴ", "動画", "名刺",
                        "口コミ", "ehaTV", "料金表", "メニュー表",
                        "Googleマップ", "駐車場アクセス", "LINE応答",
                        "マーケ", "テルミナ"]),
    ("システム・DX", ["Google", "LINE Works", "Workspace", "claude",
                      "Claude", "アカウント", "ドメイン", "PLAUD",
                      "NotebookLM", "Note book", "AIベクサム", "解析",
                      "顔写真"]),
]

SUBTASK_DONE_SUFFIX = " ✓"
SUBTASK_TODO_SUFFIX = " →未"


def http_request(method, url, *, api_key, body=None):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urlrequest.Request(url, data=data, headers=headers, method=method)
    try:
        with urlrequest.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urlerror.HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace")
        raise SystemExit(
            f"Notion API error {e.code} on {method} {url}: {body_text}"
        )


def query_database_all(api_key):
    """データベースを全件取得（ページネーション対応）。"""
    pages = []
    next_cursor = None
    while True:
        body = {"page_size": 100}
        if next_cursor:
            body["start_cursor"] = next_cursor
        res = http_request(
            "POST",
            f"{API_BASE}/databases/{DATABASE_ID}/query",
            api_key=api_key,
            body=body,
        )
        pages.extend(res.get("results", []))
        if not res.get("has_more"):
            break
        next_cursor = res.get("next_cursor")
        time.sleep(0.1)  # rate limit safety
    return pages


def get_block_children_all(api_key, block_id):
    """指定ページのブロックを全件取得（ページネーション対応）。"""
    blocks = []
    next_cursor = None
    while True:
        params = "?page_size=100"
        if next_cursor:
            params += f"&start_cursor={next_cursor}"
        res = http_request(
            "GET",
            f"{API_BASE}/blocks/{block_id}/children{params}",
            api_key=api_key,
        )
        blocks.extend(res.get("results", []))
        if not res.get("has_more"):
            break
        next_cursor = res.get("next_cursor")
        time.sleep(0.1)
    return blocks


def rich_text_to_plain(rt_array):
    if not rt_array:
        return ""
    return "".join(item.get("plain_text", "") for item in rt_array).strip()


def find_property(properties, *names):
    """プロパティ名候補のうち最初に見つかったものを返す。"""
    for name in names:
        if name in properties:
            return properties[name]
    return None


def get_title(properties):
    for prop in properties.values():
        if prop.get("type") == "title":
            return rich_text_to_plain(prop.get("title", []))
    return ""


def get_select_name(prop):
    if not prop:
        return None
    t = prop.get("type")
    if t == "select":
        v = prop.get("select")
        return v.get("name") if v else None
    if t == "status":
        v = prop.get("status")
        return v.get("name") if v else None
    if t == "multi_select":
        ms = prop.get("multi_select", [])
        return ms[0].get("name") if ms else None
    return None


def get_date_start(prop):
    if not prop:
        return None
    if prop.get("type") == "date":
        d = prop.get("date")
        return d.get("start") if d else None
    return None


def get_url(prop):
    if not prop:
        return None
    if prop.get("type") == "url":
        return prop.get("url")
    return None


def get_rich_text_plain(prop):
    if not prop:
        return ""
    if prop.get("type") == "rich_text":
        return rich_text_to_plain(prop.get("rich_text", []))
    return ""


def classify_category(name, raw_category):
    """カテゴリを7分類のいずれかに振り分ける。"""
    if raw_category and raw_category in CATEGORIES:
        return raw_category
    for category, keywords in CATEGORY_KEYWORDS:
        for kw in keywords:
            if kw in name:
                return category
    return "その他"


def normalize_size(raw_size, subtask_count):
    """工数レベルを 大/中/小 に正規化。未設定はサブタスク数で補完。"""
    if raw_size in ("大", "中", "小"):
        return raw_size
    if subtask_count >= 10:
        return "大"
    if subtask_count >= 3:
        return "中"
    return "小"


def normalize_status(raw_status):
    """ステータスを 完了/進行中/待ち/未着手 に揃える。"""
    if not raw_status:
        return "未着手"
    s = raw_status.strip()
    aliases = {
        "Done": "完了", "完了": "完了", "完成": "完了",
        "In progress": "進行中", "進行中": "進行中", "対応中": "進行中",
        "Waiting": "待ち", "待ち": "待ち", "保留": "待ち",
        "Not started": "未着手", "未着手": "未着手", "未対応": "未着手",
    }
    return aliases.get(s, s)


def format_subtask(text, checked):
    """to_doブロックを 'タスク名 ✓' / 'タスク名 →未' に整形。

    既に →... 形式のマーカーが含まれていれば未完了の追加マーカーは付けない。
    """
    text = (text or "").strip()
    if not text:
        return None
    if checked:
        return text + SUBTASK_DONE_SUFFIX
    if "→" in text:
        return text
    return text + SUBTASK_TODO_SUFFIX


def extract_subtasks(api_key, page_id):
    """ページ配下のto_doブロックをサブタスクとして取り出す。"""
    try:
        blocks = get_block_children_all(api_key, page_id)
    except SystemExit:
        raise
    except Exception as e:
        print(f"  [warn] failed to fetch blocks for {page_id}: {e}",
              file=sys.stderr)
        return []
    subtasks = []
    for b in blocks:
        if b.get("type") != "to_do":
            continue
        td = b.get("to_do", {})
        text = rich_text_to_plain(td.get("rich_text", []))
        formatted = format_subtask(text, td.get("checked", False))
        if formatted:
            subtasks.append(formatted)
    return subtasks


def transform_page(api_key, page):
    properties = page.get("properties", {})

    name = get_title(properties)
    raw_status = get_select_name(
        find_property(properties, "ステータス", "Status")
    )
    raw_priority = get_select_name(
        find_property(properties, "優先度", "Priority")
    )
    raw_size = get_select_name(
        find_property(properties, "工数レベル", "工数", "Size")
    )
    raw_category = get_select_name(
        find_property(properties, "タスクの種類", "カテゴリ", "Category")
    )

    update_date = get_date_start(find_property(properties, "更新日"))
    if not update_date:
        # フォールバック: Notion組み込みのlast_edited_timeから日付部分のみ
        let = page.get("last_edited_time", "")
        update_date = let[:10] if let else None

    due_date = get_date_start(
        find_property(properties, "期限", "Due Date", "Due date", "締切", "締切日", "deadline")
    )

    url_field = get_url(find_property(properties, "URL", "Url", "リンク"))

    subtasks = extract_subtasks(api_key, page["id"])

    size = normalize_size(raw_size, len(subtasks))
    status = normalize_status(raw_status)
    category = classify_category(name, raw_category)

    month = None
    if update_date and len(update_date) >= 7:
        try:
            month = int(update_date[5:7])
        except ValueError:
            month = None

    links = []
    if url_field:
        links.append({"label": name or "資料", "url": url_field})

    return {
        "name": name,
        "category": category,
        "status": status,
        "size": size,
        "priority": raw_priority,
        "updateDate": update_date,
        "dueDate": due_date,
        "month": month,
        "subtasks": subtasks,
        "links": links,
        "url": url_field or "",
    }


def main():
    api_key = os.environ.get("NOTION_API_KEY")
    if not api_key:
        print("ERROR: NOTION_API_KEY environment variable is not set.",
              file=sys.stderr)
        sys.exit(1)

    print(f"Querying database {DATABASE_ID} ...", file=sys.stderr)
    pages = query_database_all(api_key)
    print(f"  fetched {len(pages)} pages", file=sys.stderr)

    tasks = []
    for i, page in enumerate(pages, 1):
        print(f"  [{i}/{len(pages)}] processing {page['id']}",
              file=sys.stderr)
        tasks.append(transform_page(api_key, page))

    with open("tasks.json", "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)

    print(f"Wrote tasks.json ({len(tasks)} tasks)", file=sys.stderr)


if __name__ == "__main__":
    main()
