"""Where the pack keeps its files: ~/.youtube-operator (or $YTO_HOME).

Shared by the Lite and the Pro plugin, so upgrading keeps the profile and the weekly history.
Nothing here ever leaves the creator's machine.
"""
import datetime as _dt
import json
import os
import tempfile

SECRET_FILES = ("client.json", "token.json", "licence.json")


def home():
    p = os.environ.get("YTO_HOME") or os.path.join(os.path.expanduser("~"), ".youtube-operator")
    os.makedirs(p, exist_ok=True)
    return p


def path(*parts):
    p = os.path.join(home(), *parts)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    return p


def read_json(p, default=None):
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


def write_json(p, obj, secret=False):
    d = os.path.dirname(p)
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".tmp-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(obj, fh, ensure_ascii=False, indent=1, sort_keys=False)
            fh.write("\n")
        if secret or os.path.basename(p) in SECRET_FILES:
            os.chmod(tmp, 0o600)
        os.replace(tmp, p)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return p


def today():
    """Today's date; YTO_TODAY=YYYY-MM-DD pins it (tests, reruns)."""
    t = os.environ.get("YTO_TODAY")
    return _dt.date.fromisoformat(t) if t else _dt.date.today()


def data_end(t=None):
    """Last day the Analytics API has fully processed: YouTube documents a 48-72 h delay
    (revision history 2026-09-09), so every query ends 3 days before today."""
    return (t or today()) - _dt.timedelta(days=3)


def snapshot_path(day):
    return path("snapshots", "%s.json" % day.isoformat())


def latest_snapshot():
    d = os.path.join(home(), "snapshots")
    if not os.path.isdir(d):
        return None
    names = sorted(n for n in os.listdir(d) if n.endswith(".json") and not n.startswith("."))
    return read_json(os.path.join(d, names[-1])) if names else None


def prune(sub, days=30):
    """Delete files older than `days` in ~/.youtube-operator/<sub>. Used for public data about other
    channels: YouTube's developer policies forbid storing such statistics for more than 30 days."""
    d = os.path.join(home(), sub)
    if not os.path.isdir(d):
        return 0
    cut = today() - _dt.timedelta(days=days)
    n = 0
    for name in os.listdir(d):
        stem = name.split(".")[0]
        try:
            day = _dt.date.fromisoformat(stem[:10])
        except ValueError:
            continue
        if day < cut:
            os.remove(os.path.join(d, name))
            n += 1
    return n


def forget():
    """Remove everything the pack stored (token, profile, snapshots, caches)."""
    import shutil
    h = home()
    shutil.rmtree(h, ignore_errors=True)
    return h
