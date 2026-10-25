"""Pure computations (no network). Every function here is unit-tested with hand-checked numbers.

Our own bands (not YouTube facts, printed as "our bands" on reports):
  ABOVE >= 1.5x your median at the same age, BELOW <= 0.67x, a median needs >= MIN_REF comparable videos.
"""
import datetime as _dt
import re
import unicodedata

ABOVE, BELOW, MIN_REF = 1.5, 0.67, 5
WINDOW = 28  # first days of each video the pack pulls per day


# ---------- basics ----------

def median(xs):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2.0


def pct_change(new, old):
    if old in (None, 0) or new is None:
        return None
    return (new - old) / float(old) * 100.0


def d(s):
    return _dt.date.fromisoformat(s[:10])


def iso_duration(s):
    """ISO 8601 duration from videos.list contentDetails.duration → seconds (PT1H2M3S, P1DT2S, P0D)."""
    m = re.fullmatch(r"P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?)?", s or "")
    if not m:
        return 0
    dd, h, mi, se = (float(x) if x else 0.0 for x in m.groups())
    return int(dd * 86400 + h * 3600 + mi * 60 + se)


def clock(sec):
    sec = int(round(sec))
    h, r = divmod(sec, 3600)
    m, s = divmod(r, 60)
    return "%d:%02d:%02d" % (h, m, s) if h else "%d:%02d" % (m, s)


def parse_clock(t):
    parts = [int(p) for p in t.split(":")]
    sec = 0
    for p in parts:
        sec = sec * 60 + p
    return sec


def fold(s):
    s = unicodedata.normalize("NFKD", s or "").lower()
    return "".join(c for c in s if not unicodedata.combining(c))


def words(s):
    return [w for w in re.findall(r"[\w']+", fold(s)) if w]


# ---------- per-video daily curves ----------

def publish_day(v):
    return d(v["published"])


def days_available(v, data_end):
    """How many of the video's first WINDOW days the Analytics API has processed."""
    n = (data_end - publish_day(v)).days + 1
    return max(0, min(WINDOW, n))


def cum_at(v, k):
    """Engaged views over the video's first k days (day 1 = publish day)."""
    p = publish_day(v)
    return sum(row[1] for row in v.get("daily", []) if 0 <= (d(row[0]) - p).days < k)


def age_matched(videos, data_end, k_default=7, recent_days=WINDOW, min_ref=MIN_REF):
    """Each recent video vs the median of YOUR other videos of the same format at the same age.

    k = min(7, days available). Reference = your other videos of the same creatorContentType that
    have at least k processed days. Returns newest first.
    """
    out = []
    for v in videos:
        age = days_available(v, data_end)
        if age < 1 or (data_end - publish_day(v)).days >= recent_days:
            continue
        k = min(k_default, age)
        refs = [r for r in videos if r is not v and r.get("type") == v.get("type") and days_available(r, data_end) >= k]
        val = cum_at(v, k)
        med = median([cum_at(r, k) for r in refs]) if len(refs) >= min_ref else None
        mult = (val / med) if med else None
        out.append({
            "id": v["id"], "title": v["title"], "type": v.get("type"), "published": v["published"][:10],
            "age_days": age, "k": k, "engaged": val, "median": med, "n_ref": len(refs),
            "multiple": mult, "band": band(mult),
        })
    out.sort(key=lambda r: r["published"], reverse=True)
    return out


def band(mult):
    if mult is None:
        return "nodata"
    if mult >= ABOVE:
        return "above"
    if mult <= BELOW:
        return "below"
    return "normal"


def type_median_7d(videos, data_end, vtype, k=7):
    vals = [cum_at(v, k) for v in videos if v.get("type") == vtype and days_available(v, data_end) >= k]
    return (median(vals) if len(vals) >= MIN_REF else None), len(vals)


# ---------- channel week ----------

def window_sum(channel_daily, start, end, vtype=None):
    ev = mins = gained = lost = 0
    for row in channel_daily:
        day, t = d(row[0]), row[1]
        if start <= day <= end and (vtype is None or t == vtype):
            ev += row[2]; mins += row[4]; gained += row[5]; lost += row[6]
    return {"engaged": ev, "watch_hours": mins / 60.0, "net_subs": gained - lost, "subs_gained": gained}


def week_compare(channel_daily, data_end, days=7):
    last = window_sum(channel_daily, data_end - _dt.timedelta(days=days - 1), data_end)
    prev = window_sum(channel_daily, data_end - _dt.timedelta(days=2 * days - 1), data_end - _dt.timedelta(days=days))
    return {
        "range": [(data_end - _dt.timedelta(days=days - 1)).isoformat(), data_end.isoformat()],
        "last": last, "prev": prev,
        "change": {k: pct_change(last[k], prev[k]) for k in ("engaged", "watch_hours", "subs_gained")},
    }


def format_split(channel_daily, start, end):
    """Per creatorContentType: engaged views, watch hours and subscribers gained per 1,000 engaged views."""
    types = sorted({row[1] for row in channel_daily})
    out = []
    for t in types:
        s = window_sum(channel_daily, start, end, t)
        s["type"] = t
        s["subs_per_1k"] = (s["subs_gained"] / s["engaged"] * 1000.0) if s["engaged"] else None
        out.append(s)
    out.sort(key=lambda r: -r["engaged"])
    return out


# ---------- habits ----------

def cadence(videos, today, weeks=8):
    days = sorted(publish_day(v) for v in videos)
    last = days[-21:]                      # the last 20 gaps
    gaps = [(b - a).days for a, b in zip(last, last[1:])]
    start = today - _dt.timedelta(days=7 * weeks)
    n = sum(1 for x in days if start < x <= today)
    return {"median_gap_days": median(gaps), "uploads_per_week": n / float(weeks), "weeks": weeks,
            "last_upload": days[-1].isoformat() if days else None}


def local_weekday(published_iso, tz=None):
    t = _dt.datetime.fromisoformat(published_iso.replace("Z", "+00:00"))
    if tz:
        try:
            from zoneinfo import ZoneInfo
            t = t.astimezone(ZoneInfo(tz))
        except Exception:
            pass
    return t.weekday()  # 0 = Monday


def weekday_perf(videos, data_end, tz=None, min_n=3):
    """Median 7-day multiple (vs your format median) by the weekday you published on."""
    meds = {}
    for t in {v.get("type") for v in videos}:
        meds[t] = type_median_7d(videos, data_end, t)[0]
    groups = {}
    for v in videos:
        m = meds.get(v.get("type"))
        if not m or days_available(v, data_end) < 7:
            continue
        groups.setdefault(local_weekday(v["published"], tz), []).append(cum_at(v, 7) / m)
    rows = [{"weekday": wd, "n": len(xs), "median_multiple": median(xs)} for wd, xs in sorted(groups.items())]
    best = sorted([r for r in rows if r["n"] >= min_n], key=lambda r: -r["median_multiple"])
    return {"rows": rows, "best": [r["weekday"] for r in best[:2]], "min_n": min_n}


# ---------- metadata limits (YouTube Data API videos resource, read 2026-10-25) ----------

TITLE_MAX, DESC_MAX_BYTES, TAGS_MAX = 100, 5000, 500


def tags_length(tags):
    """Length YouTube counts for snippet.tags: commas between items count, and a tag containing a
    space counts as if wrapped in quotes ("Foo-Baz" = 7, "Foo Baz" = 9)."""
    tags = [t for t in tags if t]
    if not tags:
        return 0
    return sum(len(t) + (2 if " " in t else 0) for t in tags) + (len(tags) - 1)


def metadata_check(title="", description="", tags=None):
    tags = tags or []
    issues = []
    tl, db, tg = len(title), len(description.encode("utf-8")), tags_length(tags)
    if not title.strip():
        issues.append(("title_empty", None))
    if tl > TITLE_MAX:
        issues.append(("title_long", tl - TITLE_MAX))
    if db > DESC_MAX_BYTES:
        issues.append(("desc_long", db - DESC_MAX_BYTES))
    if tg > TAGS_MAX:
        issues.append(("tags_long", tg - TAGS_MAX))
    for field, text in (("title", title), ("description", description)):
        if "<" in text or ">" in text:
            issues.append(("angle_" + field, None))
    if any("<" in t or ">" in t for t in tags):
        issues.append(("angle_tags", None))
    return {"title_chars": tl, "desc_bytes": db, "tags_chars": tg, "issues": issues,
            "limits": {"title": TITLE_MAX, "desc": DESC_MAX_BYTES, "tags": TAGS_MAX}}


# ---------- chapters (YouTube Help 9884579, read 2026-10-25) ----------

CHAPTER_LINE = re.compile(r"^\s*\(?((?:\d{1,2}:)?\d{1,2}:\d{2})\)?\s*[-–—:|]?\s*(.*)$")


def parse_chapters(text):
    out = []
    for line in (text or "").splitlines():
        m = CHAPTER_LINE.match(line)
        if m:
            out.append((parse_clock(m.group(1)), m.group(2).strip()))
    return out


def chapters_check(chapters, duration=None):
    """Rules: first at 00:00, at least 3, ascending, each chapter at least 10 seconds."""
    issues = []
    if not chapters:
        return [("none", None)]
    if chapters[0][0] != 0:
        issues.append(("first_not_zero", clock(chapters[0][0])))
    if len(chapters) < 3:
        issues.append(("too_few", len(chapters)))
    for (a, ta), (b, tb) in zip(chapters, chapters[1:]):
        if b <= a:
            issues.append(("not_ascending", clock(b)))
        elif b - a < 10:
            issues.append(("too_short", "%s %s" % (clock(a), ta)))
    if duration and chapters and duration - chapters[-1][0] < 10:
        issues.append(("too_short", "%s %s" % (clock(chapters[-1][0]), chapters[-1][1])))
    for t, title in chapters:
        if not title:
            issues.append(("no_title", clock(t)))
    return issues


def _ts(s):
    s = s.strip().replace(",", ".")
    parts = s.split(":")
    sec = 0.0
    for p in parts:
        sec = sec * 60 + float(p)
    return sec


def parse_transcript(text):
    """SRT or WebVTT → [(start_s, end_s, text)]."""
    cues = []
    blocks = re.split(r"\n\s*\n", (text or "").replace("\r\n", "\n").replace("\r", "\n"))
    for b in blocks:
        lines = [l for l in b.split("\n") if l.strip()]
        for i, l in enumerate(lines):
            m = re.match(r"\s*([\d:.,]+)\s*-->\s*([\d:.,]+)", l)
            if m:
                body = " ".join(re.sub(r"<[^>]+>", "", x).strip() for x in lines[i + 1:])
                cues.append((_ts(m.group(1)), _ts(m.group(2)), body.strip()))
                break
    cues.sort()
    return cues


def chapters_from_transcript(cues, duration=None, count=None):
    """Proposes chapter starts at the longest pauses near evenly spaced points (>= 10 s apart).
    Claude then names each chapter from its text; `chapters --check` validates the final list."""
    if not cues:
        return []
    duration = duration or cues[-1][1]
    n = count or max(3, min(12, int(round(duration / 120.0))))
    cand = []
    for prev, cur in zip(cues, cues[1:]):
        cand.append((cur[0], max(0.0, cur[0] - prev[1])))
    starts = [0.0]
    seg = duration / n
    for i in range(1, n):
        ideal = i * seg
        window = [c for c in cand if abs(c[0] - ideal) <= seg * 0.35 and c[0] - starts[-1] >= 10 and duration - c[0] >= 10]
        if not window:
            continue
        best = max(window, key=lambda c: (c[1], -abs(c[0] - ideal)))
        starts.append(best[0])
    out = []
    for i, s in enumerate(starts):
        e = starts[i + 1] if i + 1 < len(starts) else duration
        text = " ".join(c[2] for c in cues if s <= c[0] < e)
        out.append({"start": int(s), "clock": clock(s), "seconds": int(e - s), "text": text[:240]})
    return out


# ---------- one fix (lite) ----------

def one_fix_lite(rows):
    """Pick ONE thing for this week from the age-matched rows (newest first)."""
    below = [r for r in rows if r["band"] == "below"]
    above = [r for r in rows if r["band"] == "above"]
    if below:
        r = below[0]
        return {"kind": "below", "row": r}
    if above:
        r = max(above, key=lambda x: x["multiple"])
        return {"kind": "above", "row": r}
    if rows and all(r["band"] == "nodata" for r in rows):
        return {"kind": "nodata", "row": rows[0]}
    return {"kind": "steady", "row": rows[0] if rows else None}
