#!/usr/bin/env python3
"""yto.py — YouTube Channel Operator. One command per job; prints compact Markdown for Claude to read.

  yto.py demo                              weekly report on the bundled sample channel (no sign-in)
  yto.py connect --client client.json      sign in with YOUR Google Cloud OAuth client (Desktop app), read-only
  yto.py weekly                            pull + this week vs last + every recent video vs your median + one fix
  yto.py profile [--set key=value]         the channel profile every skill reuses
  yto.py chapters --transcript f.srt | --check f.txt
  yto.py check --title "..." [--description-file f] [--tags "a,b"]
  yto.py status | forget
Pro: retention · ctr [--setup] · gaps · traffic · comments · rivals · plan · month · licence <KEY>

Options for every command: --lang en|de|es|pt|ja  --json  --demo
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from ytolib import VERSION, api, auth, calc, i18n, profile, pull, render, store  # noqa: E402

try:
    from ytolib.pro import ops as pro_ops, lic  # noqa: E402
    PRO = True
except ImportError:
    PRO = False

SAMPLES = os.path.join(os.path.dirname(HERE), "samples")
PRO_CMDS = ("retention", "ctr", "gaps", "traffic", "comments", "rivals", "plan", "month", "licence")
UPGRADE = "https://getreadystack.com/api/buy/web/youtube-channel-operator-skill-pack"


def say(s=""):
    print(s, flush=True)


def lang_for(args, prof=None):
    return i18n.lang_of(args.lang or (prof or {}).get("language") or "en")


_CLIENT = []


def client():
    """One client per run, so the units line counts every Data API call this run made."""
    if not _CLIENT:
        _CLIENT.append(api.Client(auth.access_token))
    return _CLIENT[0]


def units(L):
    if not _CLIENT:
        return None
    c = _CLIENT[0]
    return render.units_line(c.ledger.run_units(), c.ledger.today(), c.calls["analytics"], L)


def load_snapshot(args, fresh=True):
    """--demo → bundled sample; otherwise pull now (or reuse today's snapshot with --no-pull)."""
    if args.demo:
        return store.read_json(os.path.join(SAMPLES, "demo_snapshot.json"))
    if getattr(args, "no_pull", False) or not fresh:
        s = store.latest_snapshot()
        if s:
            return s
    return pull.pull(client(), max_videos=getattr(args, "max", None) or pull.MAX_VIDEOS)


def demo_profile(snap):
    p = store.read_json(os.path.join(SAMPLES, "demo_profile.json"))
    return profile.build(snap, p) if p else profile.build(snap, profile.load())


def source(args, snap):
    if args.demo:
        return pro_ops.DemoSource(store.read_json(os.path.join(SAMPLES, "demo_pro.json")), snap)
    return pro_ops.LiveSource(client(), snap)


# ---------- core commands ----------

def cmd_connect(args):
    rec = auth.connect(args.client, manual=args.manual, open_browser=not args.no_browser, pasted=args.paste, out=say)
    ch = pull.channel_info(client())
    say("Connected: %s (%s). Scopes: %s" % (ch["title"], ch["id"], rec.get("scope", "")))
    say("Read-only: the pack can read your channel and analytics; it cannot upload, edit, comment or delete.")


def cmd_pull(args):
    snap = load_snapshot(args)
    say("Pulled %d videos · data through %s\n\n%s" % (len(snap["videos"]), snap["data_end"], units(lang_for(args)) or ""))


def cmd_weekly(args):
    snap = load_snapshot(args)
    prof = demo_profile(snap) if args.demo else profile.build(snap)
    L = lang_for(args, prof)
    end = calc.d(snap["data_end"])
    week = calc.week_compare(snap["channel_daily"], end)
    rows = calc.age_matched(snap["videos"], end)
    fix = calc.one_fix_lite(rows)
    if not args.demo:
        profile.add_history(prof, week)
        profile.save(prof)
    parts = [render.header(snap, L, demo=args.demo), render.week_block(week, L), render.recent_block(rows, L)]
    fix_md, nxt = render.fix_line(fix, L), None
    pro_on = PRO and (args.demo or pro_ops.require_or_message(False, L) is None)
    if pro_on:
        blocks, pro_fix, nxt = pro_ops.weekly_pro(source(args, snap), snap, L, prof, rows)
        fix_md = pro_fix or fix_md
    parts.append("## %s\n\n**%s**" % (i18n.t("fix_title", L), fix_md))
    if nxt:
        parts.append("%s: %s" % (i18n.t("next_idea", L), nxt))
    if pro_on:
        parts += blocks
    else:
        parts.append("_%s_ %s" % (i18n.t("pro_more", L), UPGRADE))
    u = units(L)
    if u:
        parts.append(u)
    out(args, "\n\n".join(parts), {"week": week, "recent": rows, "fix": fix})


def cmd_demo(args):
    args.demo = True
    cmd_weekly(args)


def cmd_profile(args):
    prof = profile.load()
    if args.set:
        for kv in args.set:
            k, _, v = kv.partition("=")
            profile.set_field(prof, k.strip(), v.strip())
        profile.save(prof)
    if args.demo:
        prof = demo_profile(store.read_json(os.path.join(SAMPLES, "demo_snapshot.json")))
    elif args.refresh or not prof.get("numbers"):
        snap = load_snapshot(args, fresh=args.refresh)
        prof = profile.build(snap, prof)
        profile.save(prof)
    out(args, render.profile_block(prof, lang_for(args, prof)) + "\n\n`%s`" % profile.path(), prof)


def cmd_check(args):
    desc = ""
    if args.description_file:
        with open(args.description_file, encoding="utf-8") as fh:
            desc = fh.read()
    tags = [x.strip() for x in (args.tags or "").split(",") if x.strip()]
    res = calc.metadata_check(args.title or "", desc, tags)
    prof = profile.load()
    L = lang_for(args, prof)
    md = render.check_block(res, L)
    if PRO and (args.demo or pro_ops.require_or_message(False, L) is None):
        snap = load_snapshot(args, fresh=False)
        if snap:
            terms = [x[0] for x in source(args, snap).terms()] if not args.no_terms else []
            ins_md, ins = pro_ops.check_insight(snap, args.title or "", terms, L)
            md += "\n\n" + ins_md
            res["insight"] = ins
    if args.description_file and desc:
        ch = calc.parse_chapters(desc)
        if ch:
            md += "\n\n" + render.chapters_block(ch, calc.chapters_check(ch, args.duration), L)
    out(args, md, res)


def cmd_chapters(args):
    L = lang_for(args, profile.load())
    if args.check:
        with open(args.check, encoding="utf-8") as fh:
            ch = calc.parse_chapters(fh.read())
        issues = calc.chapters_check(ch, args.duration)
        out(args, render.chapters_block(ch, issues, L), {"chapters": ch, "issues": issues})
        return
    with open(args.transcript, encoding="utf-8", errors="replace") as fh:
        cues = calc.parse_transcript(fh.read())
    props = calc.chapters_from_transcript(cues, args.duration, args.count)
    out(args, render.proposed_block(props, L), props)


def cmd_status(args):
    tok = store.read_json(store.path("token.json"))
    snap = store.latest_snapshot()
    q = api.Ledger().today()
    lines = ["YouTube Channel Operator %s · edition: %s" % (VERSION, "Pro" if PRO else "Lite"),
             "data folder: %s" % store.home(),
             "connected: %s" % ("yes" if tok else "no — run connect"),
             "last snapshot: %s" % (snap["today"] + " (data through " + snap["data_end"] + ")" if snap else "none"),
             "Data API units used today (Pacific day): %d of 10,000" % q]
    if PRO:
        s = lic.status()
        lines.append("licence: %s" % s["tier"])
    out(args, "\n".join("- " + x for x in lines), {"connected": bool(tok)})


def cmd_forget(args):
    h = store.forget()
    say("Deleted %s (token, profile, snapshots, caches). To also revoke the pack's access: "
        "https://myaccount.google.com/permissions" % h)


# ---------- pro commands ----------

def pro_cmd(args):
    L = lang_for(args, profile.load())
    if not PRO:
        say("%s %s" % (i18n.t("pro_more", L), UPGRADE))
        return
    if args.cmd == "licence":
        if args.remove:
            lic.remove()
            say("licence removed")
        elif args.key:
            r = lic.enter(args.key)
            say("licence: %s" % (r.get("tier") if r.get("ok") else "not valid" + (" (offline — try again)" if r.get("offline") else "")))
        else:
            say("licence: %s" % lic.status()["tier"])
        return
    msg = pro_ops.require_or_message(args.demo, L)
    if msg:
        say(msg)
        return
    snap = load_snapshot(args, fresh=not args.no_pull)
    prof = demo_profile(snap) if args.demo else profile.load()
    if not args.demo and not prof.get("numbers"):
        prof = profile.build(snap, prof)
    src = source(args, snap)
    if args.cmd == "retention":
        md, data, _ = pro_ops.retention_cmd(src, snap, L, n=args.n, video=args.video, transcript=args.transcript)
    elif args.cmd == "ctr":
        md, data = pro_ops.ctr_cmd(src, snap, L, setup=args.setup)
    elif args.cmd == "gaps":
        md, data = pro_ops.gaps_cmd(src, snap, L)
    elif args.cmd == "traffic":
        md, data = pro_ops.traffic_cmd(src, snap, L)
    elif args.cmd == "comments":
        md, data = pro_ops.comments_cmd(src, snap, L, videos=args.videos)
    elif args.cmd == "rivals":
        md, data = pro_ops.rivals_cmd(src, snap, L, prof)
    elif args.cmd == "plan":
        md, data = pro_ops.plan_cmd(src, snap, L, prof)
    else:
        md, data = pro_ops.month_cmd(src, snap, L, prof)
    head = "# %s · %s" % (snap["channel"].get("title", ""), i18n.t("data_through", L, d=snap["data_end"]))
    if args.demo:
        head += "\n\n> " + i18n.t("demo_note", L)
    u = units(L)
    out(args, head + "\n\n" + md + ("\n\n" + u if u else ""), data)


# ---------- plumbing ----------

def out(args, md, data):
    if args.json:
        say(json.dumps(data, ensure_ascii=False, indent=1, default=str))
    else:
        say(md)


def build_parser():
    p = argparse.ArgumentParser(prog="yto.py", description="YouTube Channel Operator")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--lang")
    common.add_argument("--json", action="store_true")
    common.add_argument("--demo", action="store_true", help="use the bundled sample channel")
    common.add_argument("--no-pull", action="store_true", help="reuse the latest snapshot")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("demo", parents=[common]).set_defaults(fn=cmd_demo)
    c = sub.add_parser("connect", parents=[common])
    c.add_argument("--client", required=True, help="OAuth client JSON (type Desktop app) from Google Cloud")
    c.add_argument("--manual", action="store_true", help="paste the redirect address (remote/cloud sessions)")
    c.add_argument("--paste", help="the pasted redirect address (non-interactive --manual)")
    c.add_argument("--no-browser", action="store_true")
    c.set_defaults(fn=cmd_connect)
    x = sub.add_parser("pull", parents=[common])
    x.add_argument("--max", type=int)
    x.set_defaults(fn=cmd_pull)
    w = sub.add_parser("weekly", parents=[common])
    w.add_argument("--max", type=int)
    w.set_defaults(fn=cmd_weekly)
    pr = sub.add_parser("profile", parents=[common])
    pr.add_argument("--set", action="append", help='key=value, lists with |, e.g. voice.words_to_avoid="hack|insane"')
    pr.add_argument("--refresh", action="store_true")
    pr.set_defaults(fn=cmd_profile)
    ck = sub.add_parser("check", parents=[common])
    ck.add_argument("--title")
    ck.add_argument("--description-file")
    ck.add_argument("--tags")
    ck.add_argument("--duration", type=int)
    ck.add_argument("--no-terms", action="store_true")
    ck.set_defaults(fn=cmd_check)
    ch = sub.add_parser("chapters", parents=[common])
    g = ch.add_mutually_exclusive_group(required=True)
    g.add_argument("--transcript")
    g.add_argument("--check")
    ch.add_argument("--duration", type=int)
    ch.add_argument("--count", type=int)
    ch.set_defaults(fn=cmd_chapters)
    sub.add_parser("status", parents=[common]).set_defaults(fn=cmd_status)
    sub.add_parser("forget", parents=[common]).set_defaults(fn=cmd_forget)
    for name in PRO_CMDS:
        s = sub.add_parser(name, parents=[common])
        s.set_defaults(fn=pro_cmd)
        if name == "retention":
            s.add_argument("--video")
            s.add_argument("--n", type=int, default=8)
            s.add_argument("--transcript")
        if name == "ctr":
            s.add_argument("--setup", action="store_true")
        if name == "comments":
            s.add_argument("--videos", type=int, default=5)
        if name == "licence":
            s.add_argument("key", nargs="?")
            s.add_argument("--remove", action="store_true")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        args.fn(args)
    except auth.AuthError as e:
        say("Sign-in: %s" % e)
        return 2
    except api.ApiError as e:
        say("YouTube API: %s %s" % (e, api.hint(e)))
        return 3
    except (OSError, RuntimeError, KeyError, ValueError) as e:
        say("Error: %s" % e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
