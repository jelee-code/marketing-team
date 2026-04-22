import csv
import io
import json
import re
from datetime import datetime

import pandas as pd


def _int(x, default=0):
    if x is None:
        return default
    s = str(x).strip().replace(",", "")
    if not s or s.lower() in {"undefined", "nan", "none"}:
        return default
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return default


def _now_iso():
    return datetime.now().isoformat(timespec="seconds")


def _clean_caption(text):
    if text is None:
        return ""
    return str(text).replace("\r", "").strip()


def parse_ig_posts_csv(file_bytes: bytes) -> list[dict]:
    df = pd.read_csv(io.BytesIO(file_bytes), dtype=str, keep_default_na=False)
    now = _now_iso()
    rows = []
    for _, r in df.iterrows():
        post_id = str(r.get("게시물 ID", "")).strip()
        if not post_id:
            continue
        posted_raw = str(r.get("게시 시간", "")).strip()
        try:
            posted_at = datetime.strptime(posted_raw, "%m/%d/%Y %H:%M").isoformat()
        except ValueError:
            posted_at = posted_raw
        rows.append(
            {
                "post_id": post_id,
                "posted_at": posted_at,
                "caption": _clean_caption(r.get("설명", "")),
                "link": str(r.get("고유 링크", "")).strip(),
                "reach": _int(r.get("도달")),
                "likes": _int(r.get("좋아요")),
                "comments": _int(r.get("댓글")),
                "saves": _int(r.get("저장")),
                "shares": _int(r.get("공유")),
                "follows": _int(r.get("팔로우")),
                "views": _int(r.get("조회")),
                "imported_at": now,
            }
        )
    return rows


_TT_FORMATS = {
    # Korean "동영상" export — has saves via '즐겨찾기에 추가'.
    "ko": {
        "title": "동영상 제목",
        "link": "동영상 링크",
        "time": "게시 시간",
        "views": "동영상 조회수",
        "likes": "좋아요",
        "comments": "댓글",
        "shares": "공유",
        "saves": "즐겨찾기에 추가",
    },
    # Legacy English "Content" export (no saves column).
    "en": {
        "title": "Video title",
        "link": "Video link",
        "time": "Post time",
        "views": "Total views",
        "likes": "Total likes",
        "comments": "Total comments",
        "shares": "Total shares",
        "saves": None,
    },
}


def _detect_tt_format(df) -> dict:
    cols = set(df.columns)
    for name, schema in _TT_FORMATS.items():
        if schema["title"] in cols:
            return schema
    return _TT_FORMATS["en"]


def _parse_tt_post_time(raw: str):
    raw = (raw or "").strip()
    if not raw:
        return None
    for fmt in ("%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    for fmt in ("%B %d", "%b %d"):
        try:
            return datetime.strptime(raw, fmt).replace(year=datetime.now().year)
        except ValueError:
            continue
    return None


def parse_tt_posts_xlsx(file_bytes: bytes) -> list[dict]:
    df = pd.read_excel(io.BytesIO(file_bytes), sheet_name=0, dtype=str)
    schema = _detect_tt_format(df)
    now = _now_iso()
    today = datetime.now().date()
    rows = []
    for _, r in df.iterrows():
        link = str(r.get(schema["link"], "")).strip()
        m = re.search(r"/video/(\d+)", link)
        if not m:
            continue
        video_id = m.group(1)
        parsed_dt = _parse_tt_post_time(str(r.get(schema["time"], "")))
        posted_at = parsed_dt.isoformat() if parsed_dt else str(r.get(schema["time"], "")).strip()
        if parsed_dt and parsed_dt.date() > today:
            continue
        saves = _int(r.get(schema["saves"])) if schema["saves"] else 0
        rows.append(
            {
                "video_id": video_id,
                "posted_at": posted_at,
                "title": _clean_caption(r.get(schema["title"], "")),
                "link": link,
                "views": _int(r.get(schema["views"])),
                "likes": _int(r.get(schema["likes"])),
                "comments": _int(r.get(schema["comments"])),
                "shares": _int(r.get(schema["shares"])),
                "saves": saves,
                "imported_at": now,
            }
        )
    return rows


def parse_ig_target_csv(file_bytes: bytes) -> dict:
    # Instagram's "타겟" CSV is UTF-16 with quoted rows and section headers separated by blanks.
    try:
        text = file_bytes.decode("utf-16")
    except UnicodeDecodeError:
        text = file_bytes.decode("utf-8-sig")

    lines = [ln for ln in text.splitlines() if ln.strip() and not ln.startswith("sep=")]

    total_followers = None
    age_gender: list[dict] = []
    top_cities: list[dict] = []
    top_countries: list[dict] = []

    section = None
    for raw in lines:
        parts = next(csv.reader([raw]))
        parts = [p.strip() for p in parts]
        head = parts[0]

        if "Instagram 팔로워" == head or head.startswith("Instagram 팔로워"):
            section = "total_header"
            continue
        if "IG_ACCOUNT" in head:
            section = "total_value"
            continue
        if "성별 및 연령별" in head:
            section = "age_gender"
            continue
        if "상위 도시별" in head:
            section = "top_cities"
            continue
        if "상위 국가별" in head:
            section = "top_countries"
            continue

        if section == "total_value":
            total_followers = _int(head) or total_followers
            section = None
            continue
        if section == "age_gender":
            if head == "연령":
                continue
            if len(parts) >= 3:
                age_gender.append({"age": parts[0], "female": parts[1], "male": parts[2]})
            continue
        if section == "top_cities":
            if head in ("상위 도시",):
                continue
            if len(parts) >= 2:
                top_cities.append({"city": parts[0], "share": parts[1]})
            continue
        if section == "top_countries":
            if head in ("상위 국가",):
                continue
            if len(parts) >= 2:
                top_countries.append({"country": parts[0], "share": parts[1]})
            continue

    return {
        "snapshot_date": datetime.now().date().isoformat(),
        "total_followers": total_followers,
        "age_gender_json": json.dumps(age_gender, ensure_ascii=False),
        "top_cities_json": json.dumps(top_cities, ensure_ascii=False),
        "top_countries_json": json.dumps(top_countries, ensure_ascii=False),
    }


def _parse_english_date(s: str) -> str | None:
    s = (s or "").strip()
    if not s:
        return None
    year = datetime.now().year
    for fmt in ("%B %d", "%b %d"):
        try:
            return datetime.strptime(s, fmt).replace(year=year).date().isoformat()
        except ValueError:
            continue
    return None


def parse_tt_history_xlsx(file_bytes: bytes) -> list[dict]:
    df = pd.read_excel(io.BytesIO(file_bytes), sheet_name=0, dtype=str)
    rows = []
    for _, r in df.iterrows():
        date_iso = _parse_english_date(str(r.get("Date", "")))
        if not date_iso:
            continue
        rows.append(
            {
                "platform": "tiktok",
                "date": date_iso,
                "total_followers": _int(r.get("Followers"), default=None),
                "new_followers": _int(r.get("Difference in followers from previous day"), default=None),
            }
        )
    return rows


def parse_tt_gender_xlsx(file_bytes: bytes) -> str:
    df = pd.read_excel(io.BytesIO(file_bytes), sheet_name=0, dtype=str)
    out = []
    for _, r in df.iterrows():
        g = str(r.get("Gender", "")).strip()
        d = str(r.get("Distribution", "")).strip()
        if not g:
            continue
        try:
            pct = float(d) * 100
            d_fmt = f"{pct:.1f}%"
        except ValueError:
            d_fmt = d
        out.append({"gender": g, "share": d_fmt})
    return json.dumps(out, ensure_ascii=False)


def parse_tt_territories_xlsx(file_bytes: bytes) -> str:
    df = pd.read_excel(io.BytesIO(file_bytes), sheet_name=0, dtype=str)
    out = []
    for _, r in df.iterrows():
        c = str(r.get("Top territories", "")).strip()
        d = str(r.get("Distribution", "")).strip()
        if not c:
            continue
        try:
            pct = float(d) * 100
            d_fmt = f"{pct:.1f}%"
        except ValueError:
            d_fmt = d
        out.append({"territory": c, "share": d_fmt})
    return json.dumps(out, ensure_ascii=False)


def parse_tt_activity_xlsx(file_bytes: bytes) -> list[dict]:
    df = pd.read_excel(io.BytesIO(file_bytes), sheet_name=0, dtype=str)
    out = []
    for _, r in df.iterrows():
        date_iso = _parse_english_date(str(r.get("Date", "")))
        if not date_iso:
            continue
        try:
            hour = int(str(r.get("Hour", "")).strip())
        except ValueError:
            continue
        out.append(
            {
                "date": date_iso,
                "hour": hour,
                "active_followers": _int(r.get("Active followers")),
            }
        )
    return out


def parse_tt_daily_xlsx(file_bytes: bytes) -> list[dict]:
    """Unified TikTok daily file: 날짜 / 새 팔로워 / 총팔로워 / 도달한 시청자 / 참여 시청자."""
    df = pd.read_excel(io.BytesIO(file_bytes), sheet_name=0, dtype=str)
    rows = []
    for _, r in df.iterrows():
        date_raw = str(r.get("날짜", "")).strip()
        date_iso = None
        for fmt in ("%Y/%m/%d", "%Y-%m-%d", "%Y.%m.%d"):
            try:
                date_iso = datetime.strptime(date_raw, fmt).date().isoformat()
                break
            except ValueError:
                continue
        if not date_iso:
            continue
        rows.append(
            {
                "platform": "tiktok",
                "date": date_iso,
                "total_followers": _int(r.get("총팔로워"), default=None),
                "new_followers": _int(r.get("새 팔로워"), default=None),
                "reached_viewers": _int(r.get("도달한 시청자"), default=None),
                "engaged_viewers": _int(r.get("참여 시청자"), default=None),
            }
        )
    return rows
