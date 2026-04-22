import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "marketing.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS ig_posts (
    post_id TEXT PRIMARY KEY,
    posted_at TEXT NOT NULL,
    caption TEXT,
    link TEXT,
    reach INTEGER,
    likes INTEGER,
    comments INTEGER,
    saves INTEGER,
    shares INTEGER,
    follows INTEGER,
    views INTEGER,
    imported_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tt_posts (
    video_id TEXT PRIMARY KEY,
    posted_at TEXT NOT NULL,
    title TEXT,
    link TEXT,
    views INTEGER,
    likes INTEGER,
    comments INTEGER,
    shares INTEGER,
    saves INTEGER,
    imported_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS followers (
    platform TEXT NOT NULL,
    date TEXT NOT NULL,
    total_followers INTEGER,
    new_followers INTEGER,
    reached_viewers INTEGER,
    engaged_viewers INTEGER,
    PRIMARY KEY (platform, date)
);

CREATE TABLE IF NOT EXISTS ig_demographics (
    snapshot_date TEXT PRIMARY KEY,
    total_followers INTEGER,
    age_gender_json TEXT,
    top_cities_json TEXT,
    top_countries_json TEXT
);

CREATE TABLE IF NOT EXISTS tt_demographics (
    snapshot_date TEXT PRIMARY KEY,
    gender_json TEXT,
    top_territories_json TEXT
);

CREATE TABLE IF NOT EXISTS tt_activity (
    date TEXT NOT NULL,
    hour INTEGER NOT NULL,
    active_followers INTEGER,
    PRIMARY KEY (date, hour)
);
"""


def init():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(SCHEMA)
        for col in ("reached_viewers", "engaged_viewers"):
            try:
                conn.execute(f"ALTER TABLE followers ADD COLUMN {col} INTEGER")
            except sqlite3.OperationalError:
                pass


@contextmanager
def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def upsert_ig_posts(rows):
    if not rows:
        return 0
    sql = """
    INSERT INTO ig_posts (post_id, posted_at, caption, link, reach, likes, comments, saves, shares, follows, views, imported_at)
    VALUES (:post_id, :posted_at, :caption, :link, :reach, :likes, :comments, :saves, :shares, :follows, :views, :imported_at)
    ON CONFLICT(post_id) DO UPDATE SET
        posted_at=excluded.posted_at, caption=excluded.caption, link=excluded.link,
        reach=excluded.reach, likes=excluded.likes, comments=excluded.comments,
        saves=excluded.saves, shares=excluded.shares, follows=excluded.follows,
        views=excluded.views, imported_at=excluded.imported_at
    """
    with connect() as conn:
        conn.executemany(sql, rows)
    return len(rows)


def upsert_tt_posts(rows):
    if not rows:
        return 0
    sql = """
    INSERT INTO tt_posts (video_id, posted_at, title, link, views, likes, comments, shares, saves, imported_at)
    VALUES (:video_id, :posted_at, :title, :link, :views, :likes, :comments, :shares, :saves, :imported_at)
    ON CONFLICT(video_id) DO UPDATE SET
        posted_at=excluded.posted_at, title=excluded.title, link=excluded.link,
        views=excluded.views, likes=excluded.likes, comments=excluded.comments,
        shares=excluded.shares, saves=excluded.saves, imported_at=excluded.imported_at
    """
    with connect() as conn:
        conn.executemany(sql, rows)
    return len(rows)


def update_tt_saves(video_id, saves):
    with connect() as conn:
        conn.execute("UPDATE tt_posts SET saves = ? WHERE video_id = ?", (saves, video_id))


def upsert_follower_record(platform, date, total=None, new=None, reached=None, engaged=None):
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO followers (platform, date, total_followers, new_followers, reached_viewers, engaged_viewers)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(platform, date) DO UPDATE SET
                total_followers  = COALESCE(excluded.total_followers,  followers.total_followers),
                new_followers    = COALESCE(excluded.new_followers,    followers.new_followers),
                reached_viewers  = COALESCE(excluded.reached_viewers,  followers.reached_viewers),
                engaged_viewers  = COALESCE(excluded.engaged_viewers,  followers.engaged_viewers)
            """,
            (platform, date, total, new, reached, engaged),
        )


def delete_follower_record(platform, date):
    with connect() as conn:
        conn.execute("DELETE FROM followers WHERE platform = ? AND date = ?", (platform, date))


def _dedupe_ig_by_caption(rows):
    """Same caption can appear multiple times from Instagram glitches — keep the highest-engagement copy."""
    by_caption = {}
    passthrough = []
    for r in rows:
        key = (r.get("caption") or "").strip()
        if not key:
            passthrough.append(r)
            continue
        eng = (r.get("likes") or 0) + (r.get("comments") or 0) + (r.get("saves") or 0)
        current = by_caption.get(key)
        if current is None or eng > current[1]:
            by_caption[key] = (r, eng)
    return [r for r, _ in by_caption.values()] + passthrough


def fetch_ig_posts(dedupe=True):
    with connect() as conn:
        rows = [dict(r) for r in conn.execute("SELECT * FROM ig_posts ORDER BY posted_at DESC")]
    if dedupe:
        rows = _dedupe_ig_by_caption(rows)
        rows.sort(key=lambda r: r["posted_at"] or "", reverse=True)
    return rows


def fetch_tt_posts():
    """Exclude future-dated posts (data errors from TikTok export)."""
    cutoff = datetime.now().isoformat(timespec="seconds")
    with connect() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM tt_posts WHERE posted_at <= ? ORDER BY posted_at DESC",
            (cutoff,),
        )]


def purge_future_tt_posts():
    cutoff = datetime.now().isoformat(timespec="seconds")
    with connect() as conn:
        cur = conn.execute("DELETE FROM tt_posts WHERE posted_at > ?", (cutoff,))
        return cur.rowcount


def fetch_followers(platform=None):
    with connect() as conn:
        if platform:
            return [dict(r) for r in conn.execute("SELECT * FROM followers WHERE platform = ? ORDER BY date", (platform,))]
        return [dict(r) for r in conn.execute("SELECT * FROM followers ORDER BY platform, date")]


def latest_total(platform):
    with connect() as conn:
        row = conn.execute(
            """
            SELECT total_followers FROM followers
            WHERE platform = ? AND total_followers IS NOT NULL
            ORDER BY date DESC LIMIT 1
            """,
            (platform,),
        ).fetchone()
        return row[0] if row else None


def upsert_ig_demographics(snapshot_date, total_followers, age_gender_json, top_cities_json, top_countries_json):
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO ig_demographics (snapshot_date, total_followers, age_gender_json, top_cities_json, top_countries_json)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(snapshot_date) DO UPDATE SET
                total_followers = excluded.total_followers,
                age_gender_json = excluded.age_gender_json,
                top_cities_json = excluded.top_cities_json,
                top_countries_json = excluded.top_countries_json
            """,
            (snapshot_date, total_followers, age_gender_json, top_cities_json, top_countries_json),
        )


def latest_ig_demographics():
    with connect() as conn:
        row = conn.execute("SELECT * FROM ig_demographics ORDER BY snapshot_date DESC LIMIT 1").fetchone()
        return dict(row) if row else None


def upsert_tt_demographics(snapshot_date, gender_json=None, top_territories_json=None):
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO tt_demographics (snapshot_date, gender_json, top_territories_json)
            VALUES (?, ?, ?)
            ON CONFLICT(snapshot_date) DO UPDATE SET
                gender_json = COALESCE(excluded.gender_json, tt_demographics.gender_json),
                top_territories_json = COALESCE(excluded.top_territories_json, tt_demographics.top_territories_json)
            """,
            (snapshot_date, gender_json, top_territories_json),
        )


def latest_tt_demographics():
    with connect() as conn:
        row = conn.execute("SELECT * FROM tt_demographics ORDER BY snapshot_date DESC LIMIT 1").fetchone()
        return dict(row) if row else None


def upsert_tt_activity(rows):
    if not rows:
        return 0
    sql = """
    INSERT INTO tt_activity (date, hour, active_followers)
    VALUES (:date, :hour, :active_followers)
    ON CONFLICT(date, hour) DO UPDATE SET active_followers = excluded.active_followers
    """
    with connect() as conn:
        conn.executemany(sql, rows)
    return len(rows)


def fetch_tt_activity():
    with connect() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM tt_activity ORDER BY date, hour")]


def counts():
    with connect() as conn:
        return {
            "ig_posts": conn.execute("SELECT COUNT(*) FROM ig_posts").fetchone()[0],
            "tt_posts": conn.execute("SELECT COUNT(*) FROM tt_posts").fetchone()[0],
            "followers": conn.execute("SELECT COUNT(*) FROM followers").fetchone()[0],
            "ig_demographics": conn.execute("SELECT COUNT(*) FROM ig_demographics").fetchone()[0],
        }
