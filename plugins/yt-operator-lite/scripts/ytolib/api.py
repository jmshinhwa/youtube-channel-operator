"""HTTP to Google with the creator's own token, plus a Data API quota ledger.

Endpoints are Google's documented ones; YTO_GOOGLE_BASE=http://127.0.0.1:PORT points every one of
them at a local mock (used by the pack's own tests).
"""
import datetime as _dt
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

from . import store

# Data API v3 quota cost per call (https://developers.google.com/youtube/v3/determine_quota_cost, read 2026-10-25).
# search.list has its own bucket of 100 calls/day; everything else shares 10,000 units/day.
COST = {"channels.list": 1, "playlistItems.list": 1, "videos.list": 1, "commentThreads.list": 1,
        "playlists.list": 1, "search.list": 1}
DAILY_UNITS = 10000


def _base():
    return os.environ.get("YTO_GOOGLE_BASE", "").rstrip("/")


def url(kind):
    b = _base()
    real = {
        "auth": "https://accounts.google.com/o/oauth2/v2/auth",
        "token": "https://oauth2.googleapis.com/token",
        "data": "https://www.googleapis.com/youtube/v3",
        "analytics": "https://youtubeanalytics.googleapis.com/v2",
        "reporting": "https://youtubereporting.googleapis.com/v1",
    }[kind]
    if not b:
        return real
    return b + {"auth": "/o/oauth2/v2/auth", "token": "/token", "data": "/youtube/v3",
                "analytics": "/v2", "reporting": "/v1"}[kind]


class ApiError(Exception):
    def __init__(self, status, reason, message):
        Exception.__init__(self, "%s %s: %s" % (status, reason, message))
        self.status, self.reason, self.message = status, reason, message


HINTS = {
    "quotaExceeded": "The Data API daily quota is used up. It resets at midnight Pacific Time.",
    "forbidden": "Google refused the request. Check that YouTube Data API v3 and YouTube Analytics API are enabled in your Google Cloud project.",
    "accessNotConfigured": "Enable 'YouTube Data API v3', 'YouTube Analytics API' (and for CTR 'YouTube Reporting API') in your Google Cloud project.",
    "insufficientPermissions": "Your sign-in is missing a scope. Run connect again.",
    "authError": "Sign-in expired. Run connect again.",
}


def hint(err):
    return HINTS.get(getattr(err, "reason", ""), "")


def pacific_day():
    """Data API quota resets at midnight Pacific Time."""
    try:
        from zoneinfo import ZoneInfo
        return _dt.datetime.now(ZoneInfo("America/Los_Angeles")).date().isoformat()
    except Exception:
        return (_dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(hours=8)).date().isoformat()


class Ledger:
    """Counts Data API units this run and today (Pacific day) in ~/.youtube-operator/quota.json."""

    def __init__(self):
        self.run = {}
        self.p = store.path("quota.json")

    def add(self, method):
        units = COST.get(method, 1)
        self.run[method] = self.run.get(method, 0) + units
        q = store.read_json(self.p, {}) or {}
        day = pacific_day()
        if q.get("day") != day:
            q = {"day": day, "units": 0, "search_calls": 0}
        if method == "search.list":
            q["search_calls"] = q.get("search_calls", 0) + 1
        else:
            q["units"] = q.get("units", 0) + units
        store.write_json(self.p, q)

    def run_units(self):
        return sum(v for k, v in self.run.items() if k != "search.list")

    def today(self):
        q = store.read_json(self.p, {}) or {}
        return q.get("units", 0) if q.get("day") == pacific_day() else 0


class Client:
    def __init__(self, token_provider, ledger=None, timeout=60):
        self.token_provider = token_provider  # callable(force_refresh=False) -> access token
        self.ledger = ledger or Ledger()
        self.timeout = timeout
        self.calls = {"analytics": 0, "reporting": 0}

    def _request(self, method, full_url, body=None, headers=None, raw=False):
        last = None
        for attempt in range(3):
            tok = self.token_provider(force_refresh=(attempt > 0 and last is not None and last.status == 401))
            h = {"Authorization": "Bearer " + tok, "Accept": "application/json"}
            h.update(headers or {})
            data = None
            if body is not None:
                data = json.dumps(body).encode("utf-8")
                h["Content-Type"] = "application/json"
            req = urllib.request.Request(full_url, data=data, method=method, headers=h)
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    payload = r.read()
                    return payload if raw else json.loads(payload.decode("utf-8") or "{}")
            except urllib.error.HTTPError as e:
                last = _to_error(e)
                if e.code == 401 and attempt == 0:
                    continue
                if e.code >= 500 and attempt < 2:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                raise last
            except urllib.error.URLError as e:
                last = ApiError(0, "network", str(e.reason))
                if attempt < 2:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                raise last
        raise last

    def data(self, resource, params, method_name=None):
        """GET a Data API v3 list method, e.g. data('videos', {...}). Counts quota."""
        self.ledger.add(method_name or resource + ".list")
        q = urllib.parse.urlencode(params)
        return self._request("GET", "%s/%s?%s" % (url("data"), resource, q))

    def report(self, **params):
        """YouTube Analytics API v2 reports.query → list of row dicts."""
        self.calls["analytics"] += 1
        params.setdefault("ids", "channel==MINE")
        q = urllib.parse.urlencode(params)
        res = self._request("GET", "%s/reports?%s" % (url("analytics"), q))
        cols = [c["name"] for c in res.get("columnHeaders", [])]
        return [dict(zip(cols, row)) for row in res.get("rows", []) or []]

    def reporting(self, method, path, body=None, raw=False, absolute=False):
        self.calls["reporting"] += 1
        full = path if absolute else "%s/%s" % (url("reporting"), path.lstrip("/"))
        return self._request(method, full, body=body, raw=raw)


def _to_error(e):
    reason, message = "http%d" % e.code, e.reason
    try:
        j = json.loads(e.read().decode("utf-8"))
        err = j.get("error", {})
        if isinstance(err, dict):
            message = err.get("message", message)
            errs = err.get("errors") or []
            if errs and isinstance(errs[0], dict):
                reason = errs[0].get("reason", reason)
            elif err.get("status"):
                reason = err["status"]
        elif isinstance(err, str):
            reason, message = err, j.get("error_description", message)
    except Exception:
        pass
    if e.code == 401 and reason.startswith("http"):
        reason = "authError"
    return ApiError(e.code, reason, message)


def post_form(full_url, fields, timeout=60):
    """POST application/x-www-form-urlencoded (OAuth token endpoint)."""
    data = urllib.parse.urlencode(fields).encode("ascii")
    req = urllib.request.Request(full_url, data=data, method="POST",
                                 headers={"Content-Type": "application/x-www-form-urlencoded",
                                          "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise _to_error(e)
