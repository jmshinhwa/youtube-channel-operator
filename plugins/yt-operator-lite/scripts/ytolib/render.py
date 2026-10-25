"""Compact Markdown for Claude to read (a few hundred tokens instead of the raw API data)."""
import unicodedata

from . import calc
from .i18n import mult, num, pct, t, fmt_type


def cell(s, n=46):
    s = (s or "").replace("|", "/").replace("\n", " ")
    return s if len(s) <= n else s[: n - 1] + "…"


def width(s):
    """Terminal columns of a string (CJK characters take two)."""
    return sum(2 if unicodedata.east_asian_width(ch) in "WF" else 0 if unicodedata.combining(ch) else 1 for ch in s)


def table(head, rows):
    """Markdown table padded so it also reads well in a plain terminal."""
    rows = [[str(c) for c in r] for r in rows]
    w = [max([width(str(h))] + [width(r[i]) for r in rows] + [3]) for i, h in enumerate(head)]

    def line(cells):
        return "| " + " | ".join(c + " " * (w[i] - width(c)) for i, c in enumerate(cells)) + " |"
    return "\n".join([line([str(h) for h in head]), "|" + "|".join("-" * (x + 2) for x in w) + "|"] + [line(r) for r in rows])


def week_block(week, L):
    a, b, c = week["last"], week["prev"], week["change"]
    rows = [
        [t("m_engaged", L), num(a["engaged"], L), num(b["engaged"], L), pct(c["engaged"], L)],
        [t("m_watch", L), num(a["watch_hours"], L, 1), num(b["watch_hours"], L, 1), pct(c["watch_hours"], L)],
        [t("m_subs", L), num(a["subs_gained"], L), num(b["subs_gained"], L), pct(c["subs_gained"], L)],
        [t("m_netsubs", L), num(a["net_subs"], L), num(b["net_subs"], L), ""],
    ]
    return "## %s (%s – %s)\n\n%s" % (t("week_vs", L), week["range"][0], week["range"][1],
                                       table([t("col_metric", L), t("col_last7", L), t("col_prev7", L), t("col_change", L)], rows))


def recent_block(rows, L, limit=8):
    body = []
    for r in rows[:limit]:
        body.append([cell(r["title"]), fmt_type(r["type"], L), r["age_days"], "%s (%d)" % (num(r["engaged"], L), r["k"]),
                     num(r["median"], L), mult(r["multiple"], L) + " " + t("band_" + r["band"], L)])
    return "## %s\n\n%s\n\n_%s_" % (t("recent_title", L), table(
        [t("col_video", L), t("col_format", L), t("col_age", L), t("col_engaged_k", L), t("col_median", L), t("col_multiple", L)], body),
        t("bands_note", L))


def fix_line(fix, L):
    r = fix["row"]
    if fix["kind"] == "below":
        return t("fix_below", L, title=r["title"], x=num(r["multiple"], L, 1), k=r["k"])
    if fix["kind"] == "above":
        return t("fix_above", L, title=r["title"], x=num(r["multiple"], L, 1), k=r["k"])
    if fix["kind"] == "nodata":
        return t("fix_nodata", L, n=r["n_ref"] if r else 0)
    return t("fix_steady", L)


def header(snap, L, title_key="weekly_title", demo=False):
    ch = snap["channel"]
    h = "# %s · %s\n\n%s" % (t(title_key, L), ch.get("title", ""), t("data_through", L, d=snap["data_end"]))
    if demo:
        h += "\n\n> " + t("demo_note", L)
    return h


def units_line(run, today, analytics, L):
    return "_%s_" % t("units_line", L, run=run, today=today, a=analytics)


def profile_block(prof, L):
    n = prof.get("numbers", {})
    rows = []
    for typ, med in sorted((n.get("median_7d_engaged") or {}).items()):
        rows.append([t("p_median7", L) + " · " + fmt_type(typ, L),
                     num(med, L) if med is not None else t("p_none", L) + " (%d/5)" % n.get("videos_in_median", {}).get(typ, 0)])
    rows.append([t("p_gap", L), num(n.get("median_gap_days"), L, 1)])
    rows.append([t("p_perweek", L), num(n.get("uploads_per_week_8w"), L, 1)])
    names = t("weekday", L)
    best = n.get("best_weekdays") or []
    rows.append([t("p_weekdays", L), ", ".join(names[w] for w in best) if best else t("p_none", L)])
    rows.append([t("p_titlelen", L), num(n.get("title_len_top_quarter"), L) if n.get("title_len_top_quarter") else t("p_none", L)])
    v = prof.get("voice", {})
    voice = "; ".join("%s: %s" % (k, ", ".join(x) if isinstance(x, list) else x) for k, x in v.items() if x)
    ch = prof.get("channel", {})
    return "# %s · %s\n\n%s\n\n**%s:** %s\n\n`language=%s · timezone=%s · uploads_per_week=%s · rivals=%s`" % (
        t("profile_title", L), ch.get("title", ""), table(["", ""], rows), t("p_voice", L), voice or "—",
        prof.get("language"), prof.get("capacity", {}).get("timezone"), prof.get("capacity", {}).get("uploads_per_week"),
        ", ".join(prof.get("rivals") or []) or "—")


def check_block(res, L):
    rows = [[t("c_title", L), "%d / %d" % (res["title_chars"], res["limits"]["title"])],
            [t("c_desc", L), "%s / %s bytes" % (num(res["desc_bytes"], L), num(res["limits"]["desc"], L))],
            [t("c_tags", L), "%d / %d" % (res["tags_chars"], res["limits"]["tags"])]]
    lines = [t("i_" + code, L, n=v) if v is not None else t("i_" + code, L) for code, v in res["issues"]]
    return "## %s\n\n%s\n\n%s" % (t("check_title", L), table(["", ""], rows),
                                  "\n".join("- " + x for x in lines) if lines else "- " + t("c_ok", L))


def chapters_block(chapters, issues, L):
    lines = "\n".join("%s %s" % (calc.clock(s), title) for s, title in chapters)
    if not issues:
        verdict = "- " + t("ch_ok", L)
    else:
        verdict = "\n".join("- " + t("ch_" + code, L, v=v) for code, v in issues)
    return "## %s\n\n```\n%s\n```\n\n%s" % (t("chapters_title", L), lines, verdict)


def proposed_block(props, L):
    rows = [[p["clock"], p["seconds"], cell(p["text"], 90)] for p in props]
    return "## %s\n\n%s" % (t("ch_proposed", L), table(["start", "s", "text"], rows))
