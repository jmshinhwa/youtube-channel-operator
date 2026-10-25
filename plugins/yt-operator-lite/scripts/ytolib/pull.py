"""Pull the creator's own channel into one snapshot file (~/.youtube-operator/snapshots/<today>.json).

Data API (quota units counted): channels.list 1 + playlistItems.list 1/page + videos.list 1 per 50 ids.
Analytics API (own quota, not the 10,000 units): one per-video daily query for each video whose first
28 days are not cached yet, one lifetime query, one channel-by-day query.
"""
import datetime as _dt

from . import calc, store

MAX_VIDEOS = 60
LIFETIME_METRICS = "engagedViews,views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,subscribersGained"


def channel_info(client):
    r = client.data("channels", {"part": "snippet,contentDetails,statistics", "mine": "true"})
    items = r.get("items") or []
    if not items:
        raise RuntimeError("This Google account has no YouTube channel (channels.list mine=true is empty).")
    c = items[0]
    sn, st = c.get("snippet", {}), c.get("statistics", {})
    return {
        "id": c["id"], "title": sn.get("title", ""), "handle": sn.get("customUrl", ""),
        "country": sn.get("country"), "language": sn.get("defaultLanguage"),
        "subscribers": int(st["subscriberCount"]) if st.get("subscriberCount") and not st.get("hiddenSubscriberCount") else None,
        "video_count": int(st.get("videoCount", 0) or 0),
        "uploads": c.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads"),
    }


def upload_ids(client, playlist, limit=MAX_VIDEOS):
    ids, token = [], None
    while len(ids) < limit:
        p = {"part": "contentDetails", "playlistId": playlist, "maxResults": 50}
        if token:
            p["pageToken"] = token
        r = client.data("playlistItems", p)
        for it in r.get("items", []):
            ids.append(it["contentDetails"]["videoId"])
        token = r.get("nextPageToken")
        if not token:
            break
    return ids[:limit]


def video_details(client, ids):
    out = []
    for i in range(0, len(ids), 50):
        r = client.data("videos", {"part": "snippet,contentDetails,statistics", "id": ",".join(ids[i:i + 50]), "maxResults": 50})
        for it in r.get("items", []):
            sn, st = it.get("snippet", {}), it.get("statistics", {})
            out.append({
                "id": it["id"], "title": sn.get("title", ""), "published": sn.get("publishedAt", ""),
                "duration_s": calc.iso_duration(it.get("contentDetails", {}).get("duration")),
                "tags": sn.get("tags", []), "desc_bytes": len((sn.get("description") or "").encode("utf-8")),
                "lang": sn.get("defaultAudioLanguage") or sn.get("defaultLanguage"),
                "public": {k: int(st[k]) for k in ("viewCount", "likeCount", "commentCount") if k in st},
            })
    return out


def per_video_daily(client, v, data_end, cache):
    """First 28 days per day, split by creatorContentType (which also tells us Short vs long-form)."""
    start = calc.publish_day(v)
    end = min(start + _dt.timedelta(days=calc.WINDOW - 1), data_end)
    if end < start:
        return [], None
    c = cache.get(v["id"])
    if c and c.get("end") == end.isoformat():
        return c["daily"], c.get("type")
    rows = client.report(startDate=start.isoformat(), endDate=end.isoformat(),
                         dimensions="day,creatorContentType", filters="video==" + v["id"],
                         metrics="engagedViews,views,estimatedMinutesWatched,subscribersGained", sort="day")
    by_day, types = {}, {}
    for r in rows:
        x = by_day.setdefault(r["day"], [r["day"], 0, 0, 0, 0])
        x[1] += r.get("engagedViews", 0); x[2] += r.get("views", 0)
        x[3] += r.get("estimatedMinutesWatched", 0); x[4] += r.get("subscribersGained", 0)
        types[r["creatorContentType"]] = types.get(r["creatorContentType"], 0) + r.get("views", 0)
    daily = [by_day[k] for k in sorted(by_day)]
    vtype = max(types, key=types.get) if types else None
    cache[v["id"]] = {"end": end.isoformat(), "daily": daily, "type": vtype}
    return daily, vtype


def lifetime(client, videos, data_end):
    if not videos:
        return {}
    start = min(calc.publish_day(v) for v in videos)
    rows = client.report(startDate=start.isoformat(), endDate=data_end.isoformat(), dimensions="video",
                         filters="video==" + ",".join(v["id"] for v in videos), metrics=LIFETIME_METRICS)
    return {r["video"]: {k: r.get(k) for k in LIFETIME_METRICS.split(",")} for r in rows}


def channel_daily(client, data_end, days=56):
    start = data_end - _dt.timedelta(days=days - 1)
    rows = client.report(startDate=start.isoformat(), endDate=data_end.isoformat(),
                         dimensions="day,creatorContentType",
                         metrics="engagedViews,views,estimatedMinutesWatched,subscribersGained,subscribersLost", sort="day")
    return [[r["day"], r["creatorContentType"], r.get("engagedViews", 0), r.get("views", 0),
             r.get("estimatedMinutesWatched", 0), r.get("subscribersGained", 0), r.get("subscribersLost", 0)] for r in rows]


def pull(client, max_videos=MAX_VIDEOS, out=print):
    today = store.today()
    end = store.data_end(today)
    ch = channel_info(client)
    ids = upload_ids(client, ch["uploads"], max_videos)
    videos = video_details(client, ids)
    cache_p = store.path("cache", "video_daily.json")
    cache = store.read_json(cache_p, {}) or {}
    for v in videos:
        v["daily"], v["type"] = per_video_daily(client, v, end, cache)
    store.write_json(cache_p, cache)
    life = lifetime(client, [v for v in videos if calc.publish_day(v) <= end], end)
    for v in videos:
        v["lifetime"] = life.get(v["id"], {})
        if not v["type"]:
            v["type"] = "UNKNOWN"
    snap = {
        "schema": 1, "pulled_at": _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat(),
        "today": today.isoformat(), "data_end": end.isoformat(), "channel": ch, "videos": videos,
        "channel_daily": channel_daily(client, end),
    }
    snap["units"] = {"data_api_run": client.ledger.run_units(), "data_api_today": client.ledger.today(),
                     "daily_limit": 10000, "analytics_calls": client.calls["analytics"]}
    store.write_json(store.snapshot_path(today), snap)
    return snap
