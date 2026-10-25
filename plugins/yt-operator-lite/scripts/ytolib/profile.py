"""channel_profile.json — what every skill reads instead of asking the creator to explain the channel.

"numbers" are computed by the scripts from the creator's own data (never typed by Claude).
"voice", "capacity" and "rivals" are filled once from the creator's answers (profile --set).
"history" gets one row per weekly run, so later months can be compared.
"""
import math

from . import calc, store

DEFAULT = {
    "schema": 1,
    "channel": {},
    "language": None,
    "numbers": {},
    "voice": {"tone": "", "audience": "", "promise": "", "words_to_use": [], "words_to_avoid": [], "cta": "", "sample_lines": []},
    "capacity": {"uploads_per_week": None, "hours_per_week": None, "timezone": None},
    "rivals": [],
    "history": [],
}
SETTABLE = {"language", "voice.tone", "voice.audience", "voice.promise", "voice.words_to_use", "voice.words_to_avoid",
            "voice.cta", "voice.sample_lines", "capacity.uploads_per_week", "capacity.hours_per_week", "capacity.timezone", "rivals"}
LIST_FIELDS = {"voice.words_to_use", "voice.words_to_avoid", "voice.sample_lines", "rivals"}


def path():
    return store.path("channel_profile.json")


def load():
    p = store.read_json(path())
    prof = {k: (v.copy() if isinstance(v, (dict, list)) else v) for k, v in DEFAULT.items()}
    if p:
        for k, v in p.items():
            if isinstance(v, dict) and isinstance(prof.get(k), dict):
                prof[k].update(v)
            else:
                prof[k] = v
    return prof


def save(prof):
    store.write_json(path(), prof)
    return path()


def top_quarter_title_len(videos, data_end):
    meds = {t: calc.type_median_7d(videos, data_end, t)[0] for t in {v.get("type") for v in videos}}
    scored = [(calc.cum_at(v, 7) / meds[v["type"]], v) for v in videos
              if meds.get(v.get("type")) and calc.days_available(v, data_end) >= 7]
    if len(scored) < 8:
        return None, len(scored)
    scored.sort(key=lambda x: -x[0])
    top = scored[:int(math.ceil(len(scored) / 4.0))]
    return calc.median([len(v["title"]) for _, v in top]), len(top)


def build(snap, prof=None):
    prof = prof or load()
    end = calc.d(snap["data_end"])
    vids = snap["videos"]
    ch = snap["channel"]
    prof["channel"] = {k: ch.get(k) for k in ("id", "title", "handle", "country")}
    if not prof.get("language"):
        langs = [(v.get("lang") or "")[:2] for v in vids if v.get("lang")]
        prof["language"] = (ch.get("language") or (max(sorted(set(langs)), key=langs.count) if langs else "en"))[:2]
    n = {}
    for t in sorted({v.get("type") for v in vids}):
        med, cnt = calc.type_median_7d(vids, end, t)
        n.setdefault("median_7d_engaged", {})[t] = med
        n.setdefault("videos_in_median", {})[t] = cnt
    cad = calc.cadence(vids, end)
    n["median_gap_days"] = cad["median_gap_days"]
    n["uploads_per_week_8w"] = round(cad["uploads_per_week"], 2)
    wd = calc.weekday_perf(vids, end, prof["capacity"].get("timezone"))
    n["best_weekdays"] = wd["best"]
    n["weekday_rows"] = wd["rows"]
    tl, ntop = top_quarter_title_len(vids, end)
    n["title_len_top_quarter"] = tl
    n["computed_from"] = {"snapshot": snap["today"], "data_end": snap["data_end"], "videos": len(vids)}
    prof["numbers"].update(n)
    if prof["capacity"].get("uploads_per_week") is None and cad["uploads_per_week"]:
        prof["capacity"]["uploads_per_week"] = max(1, int(round(cad["uploads_per_week"])))
    prof["updated"] = snap["today"]
    return prof


def add_history(prof, week):
    row = {"week_end": week["range"][1], "engaged": week["last"]["engaged"],
           "watch_hours": round(week["last"]["watch_hours"], 1), "net_subs": week["last"]["net_subs"]}
    prof["history"] = [h for h in prof.get("history", []) if h.get("week_end") != row["week_end"]] + [row]
    prof["history"].sort(key=lambda h: h["week_end"])
    return prof


def set_field(prof, key, value):
    if key not in SETTABLE:
        raise KeyError("not settable: %s (settable: %s)" % (key, ", ".join(sorted(SETTABLE))))
    if key in LIST_FIELDS:
        value = [x.strip() for x in value.split("|") if x.strip()] if isinstance(value, str) else list(value)
    elif key in ("capacity.uploads_per_week", "capacity.hours_per_week"):
        value = float(value)
        value = int(value) if value.is_integer() else value
    parts = key.split(".")
    tgt = prof
    for p in parts[:-1]:
        tgt = tgt.setdefault(p, {})
    tgt[parts[-1]] = value
    return prof
