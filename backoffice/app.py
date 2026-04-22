import json
from datetime import date, datetime, timedelta
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw

import db
import exporter
import parsers


def _favicon() -> Image.Image:
    size = 128
    gradient = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(gradient)
    for x in range(size):
        t = x / (size - 1)
        r = round(224 * (1 - t) + 219 * t)
        g = round(155 * (1 - t) + 158 * t)
        b = round(207 * (1 - t) + 132 * t)
        draw.line([(x, 0), (x, size - 1)], fill=(r, g, b, 255))
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(gradient, (0, 0), mask)
    return out


st.set_page_config(page_title="콘텐츠 성과분석", page_icon=_favicon(), layout="wide")

db.init()

BASE = Path(__file__).parent
TEMPLATE_PATH = BASE / "data" / "template.xlsx"

WHITE_BLACK_CSS = """
<style>
/* Base palette */
html, body, [data-testid="stAppViewContainer"] { background: #FFFFFF; color: #000000; }
[data-testid="stSidebar"] { background: #FAFAFA; border-right: 1px solid #E5E5E5; padding-top: 1.2rem; }
h1, h2, h3, h4, h5, h6, p, label, span, div { color: #000000 !important; }

/* Tighter, roomier main content column */
[data-testid="stMainBlockContainer"] { padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1200px; }

/* Typography hierarchy */
h1 { font-size: 1.9rem !important; font-weight: 700 !important; letter-spacing: -0.01em; margin-bottom: 0.25rem !important; }
h2 { font-size: 1.35rem !important; font-weight: 700 !important; margin-top: 2.2rem !important; margin-bottom: 0.6rem !important; }
h3 { font-size: 1.05rem !important; font-weight: 600 !important; margin-top: 1.5rem !important; margin-bottom: 0.4rem !important; }

/* Caption tighter + softer */
[data-testid="stCaptionContainer"], .stCaption { margin-top: -0.35rem; color: #555 !important; font-size: 0.82rem !important; }
[data-testid="stCaptionContainer"] * { color: #555 !important; }

/* Dividers less dominant */
hr { border: 0 !important; border-top: 1px solid #EAEAEA !important; margin: 2rem 0 !important; }

/* KPI metric cards (container wraps metric + inline footnote) */
[data-testid="stMetric"] {
    padding: 0;
    background: transparent;
    border: none;
}
[data-testid="stMetric"] + [data-testid="stCaptionContainer"] {
    margin-top: 0.5rem;
    font-size: 0.72rem !important;
    color: #777 !important;
}
/* Stretch columns so KPI cards (containers) share the tallest height */
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"] { display: flex; }
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"] > [data-testid="stVerticalBlock"] { flex: 1; }
[data-testid="stHorizontalBlock"] { align-items: stretch; }
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"] [data-testid="stLayoutWrapper"] {
    flex: 1;
    border: 1px solid #ECECEC !important;
    border-radius: 6px !important;
    padding: 0.9rem 1.1rem !important;
    background: #FFFFFF;
    min-height: 160px;
    box-sizing: border-box;
    display: flex;
    flex-direction: column;
}
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"] [data-testid="stLayoutWrapper"] > [data-testid="stVerticalBlock"] {
    flex: 1;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}
[data-testid="stMetricLabel"] p { font-size: 0.82rem !important; color: #555 !important; font-weight: 500 !important; }
[data-testid="stMetricValue"] { color: #000000; font-size: 1.75rem !important; font-weight: 700 !important; }
[data-testid="stMetricDelta"] { font-size: 0.78rem !important; }

/* Buttons */
.stButton > button, .stDownloadButton > button, [data-testid="stFormSubmitButton"] > button {
    background: #FFFFFF; color: #000000; border: 1px solid #000000; border-radius: 4px;
    padding: 0.45rem 1.1rem; font-weight: 500;
    transition: all 0.12s ease;
}
.stButton > button:hover, .stDownloadButton > button:hover, [data-testid="stFormSubmitButton"] > button:hover {
    background: #000000; color: #FFFFFF;
}

/* File uploader - cleaner look */
[data-testid="stFileUploaderDropzone"] {
    border: 1px dashed #CCCCCC !important;
    background: #FAFAFA !important;
    border-radius: 6px !important;
}

/* Tables - subtle border */
[data-testid="stDataFrame"] {
    border: 1px solid #ECECEC;
    border-radius: 6px;
    overflow: hidden;
}

/* Weekly-avg HTML table */
.weekly-avg-table {
    width: 100%;
    border-collapse: collapse;
    border: 1px solid #ECECEC;
    border-radius: 6px;
    overflow: hidden;
    font-size: 0.88rem;
    margin: 0.5rem 0;
}
.weekly-avg-table th {
    background: #FAFAFA;
    padding: 0.55rem 0.9rem;
    text-align: left;
    font-weight: 600;
    border-bottom: 1px solid #ECECEC;
    color: #555 !important;
}
.weekly-avg-table td {
    padding: 0.6rem 0.9rem;
    border-bottom: 1px solid #F4F4F4;
    color: #000 !important;
}
.weekly-avg-table tr:last-child td { border-bottom: none; }
.weekly-avg-table .delta-pct {
    color: #999 !important;
    font-size: 0.82em;
    margin-left: 4px;
}

/* Charts - add breathing room */
[data-testid="stVegaLiteChart"] { padding: 0.4rem 0; }

/* Sidebar nav radio - pill/nav style */
[data-testid="stSidebar"] h1 { font-size: 1.1rem !important; padding: 0 0.5rem; }
[data-testid="stSidebar"] [role="radiogroup"] { gap: 0.2rem; }
[data-testid="stSidebar"] [role="radiogroup"] label {
    padding: 0.55rem 0.9rem;
    border-radius: 6px;
    cursor: pointer;
    transition: background 0.1s ease;
    margin: 0;
}
[data-testid="stSidebar"] [role="radiogroup"] label:hover { background: #EFEFEF; }
[data-testid="stSidebar"] [role="radiogroup"] label p { font-size: 0.95rem !important; }

/* Form inputs */
[data-baseweb="input"], [data-baseweb="select"] { border-radius: 4px !important; }

/* Alerts (success / info / warning / error) - flatter */
[data-testid="stAlert"] { border-radius: 6px; padding: 0.7rem 1rem; border: 1px solid #EAEAEA; }
</style>
"""
st.markdown(WHITE_BLACK_CSS, unsafe_allow_html=True)


def _alt_theme():
    return {
        "config": {
            "background": "#FFFFFF",
            "view": {"stroke": "#000000"},
            "axis": {"labelColor": "#000000", "titleColor": "#000000", "gridColor": "#EEEEEE", "domainColor": "#000000", "tickColor": "#000000"},
            "legend": {"labelColor": "#000000", "titleColor": "#000000"},
            "range": {"category": ["#000000", "#555555", "#999999", "#CCCCCC"]},
            "title": {"color": "#000000"},
        }
    }


alt.themes.register("bw", _alt_theme)
alt.themes.enable("bw")

COUNTRY_PALETTE = [
    "#CAEFBD", "#F3C9C4", "#4F7CC4", "#ADF0CA",
    "#C3BF83", "#280D59", "#C8E736", "#EEA881",
]

# City-name keywords that resolve to a country in the 상위 국가 list.
_CITY_COUNTRY_ALIASES = {
    "중화민국": "대만",
    "타이베이": "대만",
    "타이중": "대만",
    "가오슝": "대만",
    "타오위안": "대만",
    "타이난": "대만",
    "신베이": "대만",
    "서울": "대한민국",
    "부산": "대한민국",
    "인천": "대한민국",
    "뉴욕": "미국",
    "로스앤젤레스": "미국",
    "시카고": "미국",
    "런던": "영국",
    "파리": "프랑스",
    "도쿄": "일본",
    "오사카": "일본",
    "방콕": "태국",
    "상파울루": "브라질",
    "리우": "브라질",
    "멕시코시티": "멕시코",
}

CITY_DEFAULT_COLOR = "#999999"

_CITY_COUNTRY_PREFIXES = {
    "중화민국", "대만", "미국", "대한민국", "홍콩", "싱가포르",
    "영국", "브라질", "일본", "프랑스", "멕시코", "태국",
}


def _city_short(city: str) -> str:
    """Strip country prefix / English tokens / redundant duplicates so only the city name remains."""
    parts = (city or "").strip().split()
    if not parts:
        return city or ""
    if parts[0] in _CITY_COUNTRY_PREFIXES and len(parts) > 1:
        parts = parts[1:]

    def _has_kr(s):
        return any("\uAC00" <= ch <= "\uD7A3" for ch in s)

    if any(_has_kr(p) for p in parts):
        for i, p in enumerate(parts):
            if _has_kr(p):
                parts = parts[i:]
                break
    while len(parts) >= 2 and parts[-1] == parts[0]:
        parts = parts[:-1]
    return " ".join(parts) if parts else city.strip()


def _city_color(city: str, country_color_map: dict) -> str:
    if not city:
        return CITY_DEFAULT_COLOR
    for country, color in country_color_map.items():
        if country and country in city:
            return color
    for alias, country in _CITY_COUNTRY_ALIASES.items():
        if alias in city and country in country_color_map:
            return country_color_map[country]
    return CITY_DEFAULT_COLOR


def _page_upload():
    st.header("업로드")
    st.caption("매주 내려받는 CSV/xlsx 파일을 업로드합니다. 같은 게시물을 다시 올리면 지표가 업데이트됩니다.")

    st.subheader("1. 인스타그램 게시물 (CSV)")
    ig_file = st.file_uploader("Meta Business Suite → 콘텐츠 내보내기", type=["csv"], key="ig_posts")
    if ig_file is not None:
        try:
            rows = parsers.parse_ig_posts_csv(ig_file.getvalue())
            n = db.upsert_ig_posts(rows)
            st.success(f"인스타그램 게시물 {n}개를 불러왔습니다.")
        except Exception as e:
            st.error(f"파일을 읽는 중 오류가 발생했습니다: {e}")

    st.subheader("2. 틱톡 게시물 (xlsx)")
    tt_file = st.file_uploader("틱톡 애널리틱스 → 콘텐츠 내보내기", type=["xlsx"], key="tt_posts")
    if tt_file is not None:
        try:
            rows = parsers.parse_tt_posts_xlsx(tt_file.getvalue())
            n = db.upsert_tt_posts(rows)
            st.success(f"틱톡 게시물 {n}개를 불러왔습니다.")
        except Exception as e:
            st.error(f"파일을 읽는 중 오류가 발생했습니다: {e}")

    st.subheader("3. 인스타그램 타겟 / 인구통계 (CSV)")
    ig_target = st.file_uploader("'타겟' CSV (총 팔로워 + 연령 / 도시 / 국가)", type=["csv"], key="ig_target")
    if ig_target is not None:
        try:
            data = parsers.parse_ig_target_csv(ig_target.getvalue())
            db.upsert_ig_demographics(**data)
            st.success(f"인구통계 데이터를 저장했습니다. 총 팔로워: {data['total_followers']}")
        except Exception as e:
            st.error(f"파일을 읽는 중 오류가 발생했습니다: {e}")

    st.subheader("4. 틱톡 팔로워 · 시청자 (xlsx)")
    st.caption("틱톡 애널리틱스 '시청자' 내보내기 한 파일 (날짜 / 새 팔로워 / 총팔로워 / 도달한 시청자 / 참여 시청자).")

    tt_daily = st.file_uploader("시청자 xlsx", type=["xlsx"], key="tt_daily")
    if tt_daily is not None:
        try:
            rows = parsers.parse_tt_daily_xlsx(tt_daily.getvalue())
            for r in rows:
                db.upsert_follower_record(
                    platform=r["platform"],
                    date=r["date"],
                    total=r["total_followers"],
                    new=r["new_followers"],
                    reached=r["reached_viewers"],
                    engaged=r["engaged_viewers"],
                )
            st.success(f"틱톡 일일 데이터 {len(rows)}행을 불러왔습니다.")
        except Exception as e:
            st.error(f"파일을 읽는 중 오류가 발생했습니다: {e}")

    counts = db.counts()
    st.divider()
    st.markdown(
        f"**저장된 데이터** · 인스타 게시물: {counts['ig_posts']} · 틱톡 게시물: {counts['tt_posts']} · "
        f"팔로워 행: {counts['followers']} · 인구통계 갱신: {counts['ig_demographics']}"
    )


def _render_sortable_df(df: pd.DataFrame, key_prefix: str, link_col_name: str = None,
                         default_sort_col: str = None, default_descending: bool = True):
    cols = df.columns.tolist()
    default_idx = cols.index(default_sort_col) if (default_sort_col and default_sort_col in cols) else 0
    c1, c2 = st.columns([3, 1])
    sort_col = c1.selectbox("정렬 기준", cols, index=default_idx, key=f"{key_prefix}_col")
    sort_dir = c2.selectbox("순서", ["내림차순", "오름차순"], index=0 if default_descending else 1,
                            key=f"{key_prefix}_dir")
    try:
        df_sorted = df.sort_values(sort_col, ascending=(sort_dir == "오름차순"),
                                    na_position="last", kind="stable")
    except TypeError:
        df_sorted = df
    col_cfg = {link_col_name: st.column_config.LinkColumn(link_col_name, display_text="열기")} if link_col_name else None
    st.dataframe(df_sorted, width="stretch", hide_index=True, column_config=col_cfg)


def _page_data():
    st.header("데이터")
    st.caption("업로드된 게시물과 인구통계 원본 데이터를 표로 확인합니다.")
    st.caption("\\* 데이터는 7일마다 업데이트됩니다.")
    ig_posts = db.fetch_ig_posts()
    tt_posts = db.fetch_tt_posts()
    ig_demo = db.latest_ig_demographics()
    tt_demo = db.latest_tt_demographics()
    followers = db.fetch_followers()

    st.subheader("인스타그램 게시물")
    if ig_posts:
        df = pd.DataFrame(ig_posts)
        df["posted_at"] = pd.to_datetime(df["posted_at"], errors="coerce").dt.strftime("%Y-%m-%d")
        df["engagement"] = df["likes"].fillna(0) + df["comments"].fillna(0) + df["saves"].fillna(0)
        df = df[["posted_at", "caption", "reach", "views", "likes", "comments", "saves", "shares", "engagement", "link"]]
        df.columns = ["게시일", "캡션", "도달", "조회", "좋아요", "댓글", "저장", "공유", "인게이지먼트", "링크"]
        _render_sortable_df(df, key_prefix="ig_posts", link_col_name="링크", default_sort_col="게시일")
    else:
        st.info("인스타그램 게시물이 없습니다.")

    st.subheader("틱톡 게시물")
    if tt_posts:
        df = pd.DataFrame(tt_posts)
        df["posted_at"] = pd.to_datetime(df["posted_at"], errors="coerce").dt.strftime("%Y-%m-%d")
        df["engagement"] = df["likes"].fillna(0) + df["comments"].fillna(0) + df["shares"].fillna(0)
        df = df[["posted_at", "title", "views", "likes", "comments", "shares", "engagement", "link"]]
        df.columns = ["게시일", "제목", "조회수", "좋아요", "댓글", "공유", "인게이지먼트", "링크"]
        _render_sortable_df(df, key_prefix="tt_posts", link_col_name="링크", default_sort_col="게시일")
    else:
        st.info("틱톡 게시물이 없습니다.")

    st.divider()
    st.subheader("인스타그램 인구통계")
    if ig_demo:
        st.caption(f"마지막 갱신일: {ig_demo['snapshot_date']}")
        st.markdown("**연령 × 성별**")
        ag = json.loads(ig_demo.get("age_gender_json") or "[]")
        if ag:
            st.dataframe(pd.DataFrame(ag), hide_index=True, width="stretch")
        st.markdown("**상위 도시**")
        cities = json.loads(ig_demo.get("top_cities_json") or "[]")
        if cities:
            st.dataframe(pd.DataFrame(cities), hide_index=True, width="stretch")
        st.markdown("**상위 국가**")
        countries = json.loads(ig_demo.get("top_countries_json") or "[]")
        if countries:
            st.dataframe(pd.DataFrame(countries), hide_index=True, width="stretch")
    else:
        st.info("인스타그램 인구통계 데이터가 없습니다.")

    st.subheader("틱톡 인구통계")
    if tt_demo:
        st.caption(f"마지막 갱신일: {tt_demo['snapshot_date']}")
        st.markdown("**성별**")
        g = json.loads(tt_demo.get("gender_json") or "[]")
        if g:
            st.dataframe(pd.DataFrame(g), hide_index=True, width="stretch")
        st.markdown("**상위 국가**")
        t = json.loads(tt_demo.get("top_territories_json") or "[]")
        if t:
            st.dataframe(pd.DataFrame(t), hide_index=True, width="stretch")
    else:
        st.info("틱톡 인구통계 데이터가 없습니다.")

    st.subheader("팔로워 일별 데이터")
    if followers:
        df = pd.DataFrame(followers)
        _render_sortable_df(df, key_prefix="followers_daily", default_sort_col="date")
    else:
        st.info("팔로워 데이터가 없습니다.")


def _to_dt(s):
    if not s:
        return None
    if isinstance(s, datetime):
        return s
    try:
        return datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None


def _pct_delta(curr, prev):
    if prev in (None, 0):
        return None
    return f"{((curr - prev) / prev) * 100:+.1f}%"


def _window_sum(items, date_key, value_fn, start, end):
    total = 0
    for i in items:
        dt = _to_dt(i.get(date_key))
        if dt and start <= dt < end:
            total += value_fn(i) or 0
    return total


def _week_windows(now=None):
    now = now or datetime.now()
    last_7_end = now
    last_7_start = now - timedelta(days=7)
    prev_7_start = now - timedelta(days=14)
    return prev_7_start, last_7_start, last_7_end


def _tt_follower_7d_delta():
    rows = sorted(
        [r for r in db.fetch_followers("tiktok") if r.get("total_followers")],
        key=lambda r: r["date"],
    )
    if not rows:
        return None, None
    latest = rows[-1]
    latest_total = latest["total_followers"]
    latest_d = date.fromisoformat(latest["date"])
    target = latest_d - timedelta(days=7)
    prev = None
    for r in rows:
        d = date.fromisoformat(r["date"])
        if d <= target:
            prev = r
    if not prev:
        return latest_total, None
    diff = latest_total - prev["total_followers"]
    pct = (diff / prev["total_followers"]) * 100 if prev["total_followers"] else 0
    return latest_total, f"{diff:+,} ({pct:+.1f}%)"


def _ig_follower_7d_delta():
    # Rely on accumulated demographic snapshots for IG total-follower history.
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT snapshot_date, total_followers FROM ig_demographics ORDER BY snapshot_date"
        ).fetchall()
    rows = [dict(r) for r in rows if r["total_followers"] is not None]
    if not rows:
        return None, None
    latest = rows[-1]
    latest_total = latest["total_followers"]
    latest_d = date.fromisoformat(latest["snapshot_date"])
    target = latest_d - timedelta(days=7)
    prev = None
    for r in rows:
        d = date.fromisoformat(r["snapshot_date"])
        if d <= target:
            prev = r
    if not prev:
        return latest_total, None
    diff = latest_total - prev["total_followers"]
    pct = (diff / prev["total_followers"]) * 100 if prev["total_followers"] else 0
    return latest_total, f"{diff:+,} ({pct:+.1f}%)"


def _ig_post_engagement(p):
    return (p.get("likes") or 0) + (p.get("comments") or 0) + (p.get("saves") or 0)


def _tt_post_engagement(p):
    return (p.get("likes") or 0) + (p.get("comments") or 0) + (p.get("saves") or 0) + (p.get("shares") or 0)


def _week_delta_footnote():
    st.caption("\\* 수치와 증감은 **일주일** 기준입니다.")


def _render_weekly_avg_with_delta(df: pd.DataFrame):
    """Render weekly-avg as st.dataframe. Each numeric cell becomes 'value (±X.X%)' vs chronologically-previous week.
    Header click enables native ascending/descending sort. df is assumed sorted newest-first."""
    if df.empty:
        st.info("데이터 없음")
        return
    display = df.copy().reset_index(drop=True)
    numeric_cols = [c for c in display.columns if c != "주차"]
    for c in numeric_cols:
        new_vals = []
        for i in range(len(display)):
            val = display.loc[i, c]
            if i + 1 < len(display):
                prev = display.loc[i + 1, c]
                try:
                    prev_f, curr_f = float(prev), float(val)
                    if prev_f != 0:
                        pct = (curr_f - prev_f) / prev_f * 100
                        sign = "+" if pct >= 0 else ""
                        new_vals.append(f"{curr_f:g} ({sign}{pct:.1f}%)")
                        continue
                except (TypeError, ValueError):
                    pass
            new_vals.append(f"{float(val):g}" if isinstance(val, (int, float)) else str(val))
        display[c] = new_vals
    st.dataframe(display, hide_index=True, width="stretch")


def _monthly_weekly_avg_df(posts, metric_map):
    """Wide-format table: rows='YYYY년 M월 N주차' (week-of-month: day 1-7 = 1주차, 8-14 = 2주차, …).
    Cols = 게시물 수 + per-metric averages. Sorted newest first."""
    if not posts:
        return pd.DataFrame()
    df = pd.DataFrame(posts)
    df["posted_at"] = pd.to_datetime(df["posted_at"], errors="coerce")
    df = df.dropna(subset=["posted_at"])
    if df.empty:
        return pd.DataFrame()
    df["year"] = df["posted_at"].dt.year
    df["month"] = df["posted_at"].dt.month
    df["week_of_month"] = ((df["posted_at"].dt.day - 1) // 7) + 1
    rows = []
    for (year, month, wom), grp in df.groupby(["year", "month", "week_of_month"]):
        row = {
            "주차": f"{year}년 {month}월 {wom}주차",
            "_sort": f"{year:04d}-{month:02d}-{wom:02d}",
            "게시물 수": int(len(grp)),
        }
        for col, label in metric_map.items():
            if col in grp.columns:
                val = grp[col].mean()
                row[label] = round(float(val) if pd.notna(val) else 0, 1)
        rows.append(row)
    out = pd.DataFrame(rows).sort_values("_sort", ascending=False).drop(columns=["_sort"])
    return out.reset_index(drop=True)


def _page_ig_dashboard():
    st.header("인스타그램 대시보드")

    ig_posts = db.fetch_ig_posts()
    ig_demo = db.latest_ig_demographics()
    ig_total, ig_total_delta = _ig_follower_7d_delta()

    prev_start, last_start, now = _week_windows()
    last7_posts = _window_sum(ig_posts, "posted_at", lambda p: 1, last_start, now)
    prev7_posts = _window_sum(ig_posts, "posted_at", lambda p: 1, prev_start, last_start)
    last7_eng = _window_sum(ig_posts, "posted_at", _ig_post_engagement, last_start, now)
    prev7_eng = _window_sum(ig_posts, "posted_at", _ig_post_engagement, prev_start, last_start)
    last7_reach = _window_sum(ig_posts, "posted_at", lambda p: p.get("reach") or 0, last_start, now)
    prev7_reach = _window_sum(ig_posts, "posted_at", lambda p: p.get("reach") or 0, prev_start, last_start)

    c1, c2, c3, c4 = st.columns(4)
    with c1.container():
        st.metric("총 팔로워", f"{ig_total:,}" if ig_total else "—", delta=ig_total_delta)
        if ig_demo and ig_demo.get("snapshot_date"):
            st.caption(f"\\* 마지막 갱신: {ig_demo['snapshot_date']}")
    with c2.container():
        st.metric("게시물 수", f"{last7_posts:,}", delta=_pct_delta(last7_posts, prev7_posts))
    with c3.container():
        st.metric("인게이지먼트", f"{last7_eng:,}", delta=_pct_delta(last7_eng, prev7_eng))
    with c4.container():
        st.metric("도달", f"{last7_reach:,}", delta=_pct_delta(last7_reach, prev7_reach))
    _week_delta_footnote()

    st.divider()
    st.subheader("게시물 성과")
    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown("**Top 10 게시물**")
        if ig_posts:
            df = pd.DataFrame(ig_posts)
            df["engagement"] = df.apply(_ig_post_engagement, axis=1)
            df["label"] = df["caption"].fillna("").str.split("\n").str[0].str.slice(0, 40)
            top = df.nlargest(10, "engagement")
            chart = (
                alt.Chart(top)
                .mark_bar(color="#000000")
                .encode(
                    x=alt.X("engagement:Q", title="인게이지먼트"),
                    y=alt.Y("label:N", sort="-x", title=None),
                    tooltip=["label:N", "engagement:Q"],
                )
                .properties(height=320)
            )
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("데이터 없음")

    with col_r:
        st.markdown("**일자별 인게이지먼트**")
        if ig_posts:
            df = pd.DataFrame(ig_posts)
            df["engagement"] = df.apply(_ig_post_engagement, axis=1)
            df["posted_at"] = pd.to_datetime(df["posted_at"], errors="coerce")
            df = df.dropna(subset=["posted_at"]).copy()
            df["date"] = df["posted_at"].dt.date
            agg = df.groupby("date", as_index=False)["engagement"].sum()
            chart = (
                alt.Chart(agg)
                .mark_bar(color="#000000")
                .encode(
                    x=alt.X("date:T", title=None),
                    y=alt.Y("engagement:Q", title="인게이지먼트"),
                    tooltip=["date:T", "engagement:Q"],
                )
                .properties(height=320)
            )
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("데이터 없음")

    st.divider()
    st.subheader("주차별 게시물 평균 성과")
    ig_metric_map = {
        "reach": "도달",
        "likes": "좋아요",
        "comments": "댓글",
        "saves": "저장",
        "shares": "공유",
    }
    weekly = _monthly_weekly_avg_df(ig_posts, ig_metric_map)
    _render_weekly_avg_with_delta(weekly)
    if not weekly.empty:
        st.caption("\\* 각 달의 1\\~7일은 1주차, 8\\~14일은 2주차, 15\\~21일은 3주차, 22\\~28일은 4주차, 29일 이후는 5주차 기준입니다.")
        st.caption("\\* 주차 컬럼 헤더를 클릭하면 오름차순·내림차순 정렬됩니다.")

    st.divider()
    st.subheader("팔로워 인구통계")
    if ig_demo:
        st.caption(f"마지막 갱신일: {ig_demo['snapshot_date']}")

        st.markdown("**연령 × 성별**")
        ag = json.loads(ig_demo.get("age_gender_json") or "[]")
        if ag:
            tab_chart, tab_table = st.tabs(["그래프", "표"])
            with tab_chart:
                dfa = pd.DataFrame(ag)
                for c in ("female", "male"):
                    dfa[c] = dfa[c].str.rstrip("%").astype(float)
                melt = dfa.melt(id_vars="age", value_vars=["female", "male"], var_name="성별", value_name="비율")
                melt["성별"] = melt["성별"].map({"female": "여성", "male": "남성"})
                chart = (
                    alt.Chart(melt)
                    .mark_bar()
                    .encode(
                        x=alt.X("age:N", title=None),
                        y=alt.Y("비율:Q", title="%"),
                        color=alt.Color("성별:N",
                                        scale=alt.Scale(domain=["여성", "남성"], range=["#FABDDF", "#58A2EE"])),
                        tooltip=["age:N", "성별:N", "비율:Q"],
                    )
                    .properties(height=280)
                )
                st.altair_chart(chart, use_container_width=True)
            with tab_table:
                st.dataframe(pd.DataFrame(ag), hide_index=True, width="stretch")

        st.markdown("**상위 도시**")
        cities = json.loads(ig_demo.get("top_cities_json") or "[]")
        countries_for_map = json.loads(ig_demo.get("top_countries_json") or "[]")[: len(COUNTRY_PALETTE)]
        country_color_map = {
            c["country"]: COUNTRY_PALETTE[i] for i, c in enumerate(countries_for_map)
        }
        if cities:
            tab_chart, tab_table = st.tabs(["그래프", "표"])
            with tab_chart:
                dfc = pd.DataFrame(cities).head(10)
                dfc["비율"] = dfc["share"].str.rstrip("%").astype(float)
                dfc["도시"] = dfc["city"].apply(_city_short)
                dfc["색상"] = dfc["city"].apply(lambda c: _city_color(c, country_color_map))
                chart = (
                    alt.Chart(dfc)
                    .mark_bar()
                    .encode(
                        x=alt.X("비율:Q", title="%"),
                        y=alt.Y("도시:N", sort="-x", title=None, axis=alt.Axis(labelLimit=300)),
                        color=alt.Color("색상:N", scale=None, legend=None),
                        tooltip=[alt.Tooltip("city:N", title="원본"), alt.Tooltip("도시:N"), alt.Tooltip("share:N")],
                    )
                    .properties(height=320)
                )
                st.altair_chart(chart, use_container_width=True)
            with tab_table:
                st.dataframe(pd.DataFrame(cities).head(10), hide_index=True, width="stretch")

        st.markdown("**상위 국가**")
        countries = json.loads(ig_demo.get("top_countries_json") or "[]")
        if countries:
            tab_chart, tab_table = st.tabs(["그래프", "표"])
            with tab_chart:
                dfo = pd.DataFrame(countries).head(len(COUNTRY_PALETTE))
                dfo["비율"] = dfo["share"].str.rstrip("%").astype(float)
                domain = dfo["country"].tolist()
                chart = (
                    alt.Chart(dfo)
                    .mark_arc(outerRadius=140, innerRadius=80)
                    .encode(
                        theta=alt.Theta("비율:Q", sort=alt.SortField("비율", order="descending")),
                        color=alt.Color(
                            "country:N",
                            scale=alt.Scale(domain=domain, range=COUNTRY_PALETTE[: len(domain)]),
                            legend=alt.Legend(
                                title=None,
                                orient="right",
                                direction="vertical",
                                columns=1,
                                symbolType="square",
                                offset=25,
                                labelLimit=160,
                            ),
                        ),
                        order=alt.Order("비율:Q", sort="descending"),
                        tooltip=["country:N", "share:N"],
                    )
                    .properties(height=460, padding={"top": 15, "bottom": 15, "left": 10, "right": 10})
                    .configure_view(strokeOpacity=0)
                )
                st.altair_chart(chart, use_container_width=True)
            with tab_table:
                st.dataframe(pd.DataFrame(countries).head(len(COUNTRY_PALETTE)), hide_index=True, width="stretch")
    else:
        st.info("인구통계 데이터가 없습니다.")


def _page_tt_dashboard():
    st.header("틱톡 대시보드")

    tt_posts = db.fetch_tt_posts()
    tt_demo = db.latest_tt_demographics()
    followers = db.fetch_followers("tiktok")
    activity = db.fetch_tt_activity()

    tt_total, tt_total_delta = _tt_follower_7d_delta()
    prev_start, last_start, now = _week_windows()
    last7_posts = _window_sum(tt_posts, "posted_at", lambda p: 1, last_start, now)
    prev7_posts = _window_sum(tt_posts, "posted_at", lambda p: 1, prev_start, last_start)
    last7_eng = _window_sum(tt_posts, "posted_at", _tt_post_engagement, last_start, now)
    prev7_eng = _window_sum(tt_posts, "posted_at", _tt_post_engagement, prev_start, last_start)
    last7_views = _window_sum(tt_posts, "posted_at", lambda p: p.get("views") or 0, last_start, now)
    prev7_views = _window_sum(tt_posts, "posted_at", lambda p: p.get("views") or 0, prev_start, last_start)

    tt_latest_date = None
    tt_followers_sorted = sorted([r for r in followers if r.get("total_followers")], key=lambda r: r["date"])
    if tt_followers_sorted:
        tt_latest_date = tt_followers_sorted[-1]["date"]

    c1, c2, c3, c4 = st.columns(4)
    with c1.container():
        st.metric("총 팔로워", f"{tt_total:,}" if tt_total else "—", delta=tt_total_delta)
        if tt_latest_date:
            st.caption(f"\\* 마지막 갱신: {tt_latest_date}")
    with c2.container():
        st.metric("게시물 수", f"{last7_posts:,}", delta=_pct_delta(last7_posts, prev7_posts))
    with c3.container():
        st.metric("인게이지먼트", f"{last7_eng:,}", delta=_pct_delta(last7_eng, prev7_eng))
    with c4.container():
        st.metric("조회수", f"{last7_views:,}", delta=_pct_delta(last7_views, prev7_views))
    _week_delta_footnote()

    st.divider()
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("팔로워 추이")
        tt_hist = [r for r in followers if r.get("total_followers")]
        if tt_hist:
            df = pd.DataFrame(tt_hist)
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            chart = (
                alt.Chart(df)
                .mark_line(color="#000000", point=alt.OverlayMarkDef(color="#000000", size=40))
                .encode(
                    x=alt.X("date:T", title=None),
                    y=alt.Y("total_followers:Q", title="총 팔로워", scale=alt.Scale(zero=False)),
                    tooltip=["date:T", "total_followers:Q"],
                )
                .properties(height=260)
            )
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("데이터 없음")
    with col_b:
        st.subheader("일별 팔로워 증감률")
        f_rows = [r for r in followers if r.get("total_followers")]
        if f_rows:
            df = pd.DataFrame(f_rows)
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            df = df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
            df["prev_total"] = df["total_followers"].shift(1)
            df["증감률"] = (df["total_followers"] - df["prev_total"]) / df["prev_total"] * 100
            plot_df = df.dropna(subset=["증감률"])
            if not plot_df.empty:
                chart = (
                    alt.Chart(plot_df)
                    .mark_bar(color="#000000")
                    .encode(
                        x=alt.X("date:T", title=None),
                        y=alt.Y("증감률:Q", title="증감률 (%)"),
                        tooltip=["date:T", alt.Tooltip("증감률:Q", format="+.2f", title="증감률 (%)")],
                    )
                    .properties(height=260)
                )
                st.altair_chart(chart, use_container_width=True)
            else:
                st.info("데이터 없음")
        else:
            st.info("데이터 없음")

    st.divider()
    st.subheader("게시물 성과")
    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown("**Top 10 게시물**")
        if tt_posts:
            df = pd.DataFrame(tt_posts)
            df["engagement"] = df.apply(_tt_post_engagement, axis=1)
            df["label"] = df["title"].fillna("").str.split("\n").str[0].str.slice(0, 40)
            top = df.nlargest(10, "engagement")
            chart = (
                alt.Chart(top)
                .mark_bar(color="#000000")
                .encode(
                    x=alt.X("engagement:Q", title="인게이지먼트"),
                    y=alt.Y("label:N", sort="-x", title=None),
                    tooltip=["label:N", "engagement:Q"],
                )
                .properties(height=320)
            )
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("데이터 없음")
    with col_r:
        st.markdown("**일자별 인게이지먼트**")
        if tt_posts:
            df = pd.DataFrame(tt_posts)
            df["engagement"] = df.apply(_tt_post_engagement, axis=1)
            df["posted_at"] = pd.to_datetime(df["posted_at"], errors="coerce")
            df = df.dropna(subset=["posted_at"]).copy()
            df["date"] = df["posted_at"].dt.date
            agg = df.groupby("date", as_index=False)["engagement"].sum()
            chart = (
                alt.Chart(agg)
                .mark_bar(color="#000000")
                .encode(
                    x=alt.X("date:T", title=None),
                    y=alt.Y("engagement:Q", title="인게이지먼트"),
                    tooltip=["date:T", "engagement:Q"],
                )
                .properties(height=320)
            )
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("데이터 없음")

    st.divider()
    st.subheader("주차별 게시물 평균 성과")
    tt_metric_map = {
        "views": "조회수",
        "likes": "좋아요",
        "comments": "댓글",
        "shares": "공유",
    }
    weekly = _monthly_weekly_avg_df(tt_posts, tt_metric_map)
    _render_weekly_avg_with_delta(weekly)
    if not weekly.empty:
        st.caption("\\* 각 달의 1\\~7일은 1주차, 8\\~14일은 2주차, 15\\~21일은 3주차, 22\\~28일은 4주차, 29일 이후는 5주차 기준입니다.")
        st.caption("\\* 주차 컬럼 헤더를 클릭하면 오름차순·내림차순 정렬됩니다.")

    st.divider()
    st.subheader("팔로워 인구통계")
    if tt_demo:
        st.caption(f"마지막 갱신일: {tt_demo['snapshot_date']}")
        demo_cols = st.columns(2)
        with demo_cols[0]:
            st.markdown("**성별**")
            g = json.loads(tt_demo.get("gender_json") or "[]")
            if g:
                tab_chart, tab_table = st.tabs(["그래프", "표"])
                with tab_chart:
                    dfg = pd.DataFrame(g)
                    dfg["비율"] = dfg["share"].str.rstrip("%").astype(float)
                    dfg["gender_ko"] = dfg["gender"].map({"Female": "여성", "Male": "남성", "Other": "기타"}).fillna(dfg["gender"])
                    chart = (
                        alt.Chart(dfg)
                        .mark_arc(outerRadius=140, innerRadius=80)
                        .encode(
                            theta=alt.Theta("비율:Q", sort=alt.SortField("비율", order="descending")),
                            color=alt.Color("gender_ko:N",
                                            scale=alt.Scale(domain=["여성", "남성", "기타"],
                                                            range=["#FABDDF", "#58A2EE", "#23162C"]),
                                            legend=alt.Legend(
                                                title=None,
                                                orient="right",
                                                direction="vertical",
                                                columns=1,
                                                symbolType="square",
                                                offset=25,
                                            )),
                            order=alt.Order("비율:Q", sort="descending"),
                            tooltip=["gender_ko:N", "share:N"],
                        )
                        .properties(height=460, padding={"top": 15, "bottom": 15, "left": 10, "right": 10})
                        .configure_view(strokeOpacity=0)
                    )
                    st.altair_chart(chart, use_container_width=True)
                with tab_table:
                    st.dataframe(pd.DataFrame(g), hide_index=True, width="stretch")
        with demo_cols[1]:
            st.markdown("**상위 국가**")
            t = json.loads(tt_demo.get("top_territories_json") or "[]")
            if t:
                tab_chart, tab_table = st.tabs(["그래프", "표"])
                with tab_chart:
                    dft = pd.DataFrame(t)
                    dft = dft[dft["territory"] != "Others"].head(len(COUNTRY_PALETTE))
                    dft["비율"] = dft["share"].str.rstrip("%").astype(float)
                    domain = dft["territory"].tolist()
                    chart = (
                        alt.Chart(dft)
                        .mark_arc(outerRadius=140, innerRadius=80)
                        .encode(
                            theta=alt.Theta("비율:Q", sort=alt.SortField("비율", order="descending")),
                            color=alt.Color(
                                "territory:N",
                                scale=alt.Scale(domain=domain, range=COUNTRY_PALETTE[: len(domain)]),
                                legend=alt.Legend(
                                    title=None,
                                    orient="right",
                                    direction="vertical",
                                    columns=1,
                                    symbolType="square",
                                    offset=25,
                                    labelLimit=160,
                                ),
                            ),
                            order=alt.Order("비율:Q", sort="descending"),
                            tooltip=["territory:N", "share:N"],
                        )
                        .properties(height=460, padding={"top": 15, "bottom": 15, "left": 10, "right": 10})
                        .configure_view(strokeOpacity=0)
                    )
                    st.altair_chart(chart, use_container_width=True)
                with tab_table:
                    st.dataframe(pd.DataFrame(t), hide_index=True, width="stretch")
    else:
        st.info("인구통계 데이터가 없습니다.")

    viewer_rows = [r for r in followers if r.get("reached_viewers") is not None or r.get("engaged_viewers") is not None]
    if viewer_rows:
        st.divider()
        st.subheader("일별 시청자")
        dfv = pd.DataFrame(viewer_rows)
        dfv["date"] = pd.to_datetime(dfv["date"], errors="coerce")
        dfv = dfv.dropna(subset=["date"])
        melt = dfv.melt(id_vars="date", value_vars=["reached_viewers", "engaged_viewers"],
                        var_name="구분", value_name="시청자 수")
        melt["구분"] = melt["구분"].map({"reached_viewers": "도달한 시청자", "engaged_viewers": "참여 시청자"})
        chart = (
            alt.Chart(melt.dropna(subset=["시청자 수"]))
            .mark_line(point=True)
            .encode(
                x=alt.X("date:T", title=None),
                y=alt.Y("시청자 수:Q"),
                color=alt.Color("구분:N",
                                scale=alt.Scale(domain=["도달한 시청자", "참여 시청자"], range=["#000000", "#4F7CC4"]),
                                legend=alt.Legend(title=None, orient="bottom")),
                tooltip=["date:T", "구분:N", "시청자 수:Q"],
            )
            .properties(height=240)
        )
        st.altair_chart(chart, use_container_width=True)

    if activity:
        st.divider()
        st.subheader("시간대별 활성 팔로워")
        dfa = pd.DataFrame(activity)
        avg = dfa.groupby("hour", as_index=False)["active_followers"].mean()
        chart = (
            alt.Chart(avg)
            .mark_bar(color="#000000")
            .encode(
                x=alt.X("hour:O", title="시간대"),
                y=alt.Y("active_followers:Q", title="평균 활성 팔로워"),
                tooltip=["hour:O", "active_followers:Q"],
            )
            .properties(height=240)
        )
        st.altair_chart(chart, use_container_width=True)


def _page_export():
    st.header("엑셀 내보내기")
    st.caption("기존 엑셀을 최신 데이터로 다시 생성합니다. 차트와 서식은 그대로 유지됩니다.")
    if not exporter.template_exists():
        st.warning("템플릿이 아직 업로드되지 않았습니다. 설정 페이지에서 올려주세요.")
        return
    if st.button("엑셀 생성"):
        out = BASE / "data" / f"콘텐츠_마케터_성과분석_{datetime.now():%Y%m%d_%H%M}.xlsx"
        exporter.build_xlsx(out)
        with open(out, "rb") as f:
            st.download_button(
                "다운로드",
                data=f.read(),
                file_name=out.name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        st.success(f"{out.name} 파일을 생성했습니다.")


def _page_settings():
    st.header("설정")
    st.subheader("템플릿 엑셀")
    st.caption("최초 1회 설정입니다. 기존 콘텐츠_마케터_성과분석.xlsx를 업로드하면 내보내기 시 해당 템플릿을 채우고 차트를 유지합니다.")
    if TEMPLATE_PATH.exists():
        st.success(f"템플릿이 설치되어 있습니다: {TEMPLATE_PATH}")
    up = st.file_uploader("템플릿 .xlsx 업로드", type=["xlsx"], key="template")
    if up is not None:
        TEMPLATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(TEMPLATE_PATH, "wb") as f:
            f.write(up.getvalue())
        st.success("템플릿을 저장했습니다. 페이지를 새로고침하세요.")

    st.divider()
    st.subheader("데이터 초기화")
    if st.button("저장된 모든 데이터 삭제"):
        for tbl in ("ig_posts", "tt_posts", "followers", "ig_demographics", "tt_demographics", "tt_activity"):
            with db.connect() as conn:
                conn.execute(f"DELETE FROM {tbl}")
        st.success("모든 데이터를 삭제했습니다.")


PAGES = {
    "IG": _page_ig_dashboard,
    "TT": _page_tt_dashboard,
    "데이터": _page_data,
    "업로드": _page_upload,
    "엑셀 내보내기": _page_export,
    "설정": _page_settings,
}

st.sidebar.title("콘텐츠 성과분석")
page = st.sidebar.radio("메뉴", list(PAGES.keys()), label_visibility="collapsed")
PAGES[page]()
