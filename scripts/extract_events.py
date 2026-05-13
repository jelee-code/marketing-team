"""Extract dated future events from namu.wiki page text and match against artist DB."""
import json
import re
import sys
from datetime import date

NAMU_TXT = r"C:\Users\imaji\AppData\Local\Temp\namu.txt"
ARTIST_DB = "data/artist-db.json"
TODAY = date(2026, 5, 13)
YEAR = 2026

EVENT_KEYWORDS = {
    "컴백": "컴백",
    "발매": "발매",
    "데뷔": "데뷔",
    "콘서트": "콘서트",
    "팬미팅": "팬미팅",
    "OST": "OST",
    "발표": "발매",
    "공개": "발매",
}

def load_artist_db():
    with open(ARTIST_DB, "r", encoding="utf-8") as f:
        return json.load(f)

def normalize(s):
    return re.sub(r"\s+", "", s).lower()

def build_search_index(db):
    """Map every search term -> (canonical_name, type='group'|'member', group)."""
    idx = []
    for g in db["groups"]:
        names = set()
        for k in ("nameKR", "nameEN", "nameShort"):
            v = g.get(k, "")
            if v:
                names.add(v)
        for term in re.split(r"\s+", g.get("searchTerms", "")):
            if len(term) >= 2:
                names.add(term)
        for n in names:
            n_norm = normalize(n)
            if len(n_norm) >= 2:
                idx.append((n_norm, g["nameKR"], "group", ""))
    for m in db["members"]:
        names = set()
        for k in ("nameKR", "nameEN"):
            v = m.get(k, "")
            if v:
                names.add(v)
        for term in re.split(r"\s+", m.get("searchTerms", "")):
            if len(term) >= 2:
                names.add(term)
        for n in names:
            n_norm = normalize(n)
            if len(n_norm) >= 2:
                idx.append((n_norm, m["nameKR"], "member", m.get("group", "")))
    # Sort longest first so longer matches win
    idx.sort(key=lambda x: -len(x[0]))
    return idx

def extract_events(text):
    """Split text by 'X월 Y일,' markers so each event gets its own body."""
    events = []
    # Find all date markers and their positions
    marker = re.compile(r"(\d{1,2})월\s*(\d{1,2})일\s*,")
    matches = list(marker.finditer(text))
    for i, m in enumerate(matches):
        month = int(m.group(1))
        day = int(m.group(2))
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        # Stop at sectional boundaries
        for cutter in ["2.2.", "2.3.", "2.4.", "3.", "4.", "5."]:
            ci = body.find(cutter)
            if 0 < ci < len(body):
                body = body[:ci]
        # Stop at next-month header like "6월 " (no day, just month + content)
        m2 = re.search(r"\b\d{1,2}월\s+[가-힣A-Z]", body)
        if m2 and m2.start() > 20:
            body = body[: m2.start()]
        try:
            dt = date(YEAR, month, day)
        except ValueError:
            continue
        events.append({"date": dt.isoformat(), "body": body})
    return events

def detect_event_type(body):
    types = []
    for kw, label in EVENT_KEYWORDS.items():
        if kw in body and label not in types:
            types.append(label)
    if "데뷔할 예정" in body or "데뷔를 할 예정" in body:
        types = ["데뷔"] + [t for t in types if t != "데뷔"]
    if "콘서트" in body:
        types = ["콘서트"] + [t for t in types if t != "콘서트"]
    if not types:
        types = ["기타"]
    return types

def match_artists(body, idx):
    """Return list of (canonical_name, type, group) found in body."""
    body_norm = normalize(body)
    found = []
    seen_canonical = set()
    for term_norm, canonical, kind, group in idx:
        if term_norm in body_norm and canonical not in seen_canonical:
            found.append((canonical, kind, group))
            seen_canonical.add(canonical)
    return found

def main():
    with open(NAMU_TXT, "r", encoding="utf-8") as f:
        text = f.read()
    db = load_artist_db()
    idx = build_search_index(db)
    events = extract_events(text)

    future = [e for e in events if e["date"] >= TODAY.isoformat()]
    print(f"Total events parsed: {len(events)}", file=sys.stderr)
    print(f"Future events (>= {TODAY}): {len(future)}", file=sys.stderr)

    out = []
    for ev in future:
        only_future = ev["date"] >= TODAY.isoformat()
        if not only_future:
            continue
        artists = match_artists(ev["body"], idx)
        if not artists:
            continue
        types = detect_event_type(ev["body"])
        for canonical, kind, group in artists:
            out.append({
                "date": ev["date"],
                "artist": canonical,
                "type": kind,
                "group": group,
                "tags": types,
                "snippet": ev["body"][:160],
            })

    print(json.dumps(out, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
