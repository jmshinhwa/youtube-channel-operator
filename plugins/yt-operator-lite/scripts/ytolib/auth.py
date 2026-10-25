"""Sign in with the creator's OWN Google Cloud OAuth client (type: Desktop app).

OAuth 2.0 for desktop apps with PKCE (S256) and a loopback redirect http://127.0.0.1:<port>,
as Google documents for desktop clients. Read-only scopes only: the pack never uploads, edits,
comments or deletes anything. `--manual` works where no browser can reach this machine
(remote or cloud sessions): you paste the address the browser lands on.
"""
import base64
import hashlib
import http.server
import os
import secrets
import threading
import time
import urllib.parse
import webbrowser

from . import api, store

SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",       # channel, uploads, comments (and required by reports.query)
    "https://www.googleapis.com/auth/yt-analytics.readonly",  # Analytics reports + Reporting API (reach / CTR)
]
MANUAL_PORT = 8765


class AuthError(Exception):
    pass


def load_client(p):
    j = store.read_json(p)
    if not j:
        raise AuthError("Cannot read %s. Download the OAuth client JSON (type 'Desktop app') from Google Cloud > APIs & Services > Credentials." % p)
    c = j.get("installed") or j.get("web") or j
    if "client_id" not in c:
        raise AuthError("%s has no client_id. Use the JSON of an OAuth client of type 'Desktop app'." % p)
    return {"client_id": c["client_id"], "client_secret": c.get("client_secret", "")}


def pkce_pair():
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode("ascii")
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).rstrip(b"=").decode("ascii")
    return verifier, challenge


def auth_url(client_id, redirect_uri, challenge, state):
    q = {
        "client_id": client_id, "redirect_uri": redirect_uri, "response_type": "code",
        "scope": " ".join(SCOPES), "code_challenge": challenge, "code_challenge_method": "S256",
        "state": state, "access_type": "offline", "prompt": "consent",
    }
    return api.url("auth") + "?" + urllib.parse.urlencode(q)


class _Catch(http.server.BaseHTTPRequestHandler):
    result = None

    def do_GET(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        type(self).result = {k: v[0] for k, v in q.items()}
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        ok = "code" in type(self).result
        msg = ("Signed in. You can close this tab and go back to Claude." if ok
               else "Sign-in was not completed: %s" % type(self).result.get("error", "unknown"))
        self.wfile.write(("<!doctype html><meta charset=utf-8><title>YouTube Channel Operator</title>"
                          "<p style='font:16px system-ui;margin:3em'>%s</p>" % msg).encode("utf-8"))

    def log_message(self, *a):
        pass


def _wait_loopback(timeout):
    srv = http.server.HTTPServer(("127.0.0.1", 0), _Catch)
    _Catch.result = None
    srv.timeout = 1
    port = srv.server_address[1]

    def loop():
        end = time.time() + timeout
        while _Catch.result is None and time.time() < end:
            srv.handle_request()
    t = threading.Thread(target=loop, daemon=True)
    return srv, port, t


def parse_pasted(text):
    """Accept the full address the browser landed on, or just the code."""
    text = (text or "").strip()
    if text.startswith("http"):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(text).query)
        return {k: v[0] for k, v in q.items()}
    return {"code": text}


def exchange(client, code, verifier, redirect_uri):
    tok = api.post_form(api.url("token"), {
        "code": code, "client_id": client["client_id"], "client_secret": client["client_secret"],
        "redirect_uri": redirect_uri, "grant_type": "authorization_code", "code_verifier": verifier,
    })
    return _save_token(tok)


def _save_token(tok, keep_refresh=None):
    rec = {
        "access_token": tok["access_token"],
        "refresh_token": tok.get("refresh_token") or keep_refresh,
        "expires_at": int(time.time()) + int(tok.get("expires_in", 3600)),
        "scope": tok.get("scope", " ".join(SCOPES)),
    }
    store.write_json(store.path("token.json"), rec, secret=True)
    return rec


def connect(client_json, manual=False, open_browser=True, timeout=300, pasted=None, out=print):
    client = load_client(client_json)
    store.write_json(store.path("client.json"), client, secret=True)
    verifier, challenge = pkce_pair()
    state = secrets.token_urlsafe(16)
    if manual:
        redirect = "http://127.0.0.1:%d" % MANUAL_PORT
        out("1. Open this address and sign in with the Google account that owns the channel:\n\n" + auth_url(client["client_id"], redirect, challenge, state) + "\n")
        out("2. The browser then shows 'This site can't be reached' on 127.0.0.1 — that is expected.\n   Copy the whole address from the address bar and paste it here.")
        got = parse_pasted(pasted if pasted is not None else input("> "))
    else:
        srv, port, t = _wait_loopback(timeout)
        redirect = "http://127.0.0.1:%d" % port
        u = auth_url(client["client_id"], redirect, challenge, state)
        out("Opening Google sign-in. If no browser opens, open this address:\n\n" + u + "\n")
        t.start()
        if open_browser and not os.environ.get("YTO_NO_BROWSER"):
            try:
                webbrowser.open(u)
            except Exception:
                pass
        t.join(timeout + 2)
        srv.server_close()
        got = _Catch.result or {}
    if "error" in got:
        raise AuthError("Google returned: %s" % got["error"])
    if "code" not in got:
        raise AuthError("No sign-in code received.")
    if "state" in got and got["state"] != state:
        raise AuthError("State mismatch — start connect again.")
    return exchange(client, got["code"], verifier, redirect)


def access_token(force_refresh=False):
    tok = store.read_json(store.path("token.json"))
    if not tok:
        raise AuthError("Not connected yet. Run: yto.py connect --client <your-client.json>")
    if not force_refresh and tok.get("expires_at", 0) - 60 > time.time():
        return tok["access_token"]
    client = store.read_json(store.path("client.json"))
    if not client or not tok.get("refresh_token"):
        raise AuthError("Sign-in expired. Run connect again.")
    try:
        new = api.post_form(api.url("token"), {
            "client_id": client["client_id"], "client_secret": client.get("client_secret", ""),
            "refresh_token": tok["refresh_token"], "grant_type": "refresh_token"})
    except api.ApiError as e:
        if e.reason in ("invalid_grant", "authError") or e.status in (400, 401):
            raise AuthError("Google ended the sign-in (%s). Run connect again. If your OAuth consent screen is "
                            "in 'Testing', Google expires the sign-in after 7 days; set it to 'In production' to avoid this." % e.reason)
        raise
    return _save_token(new, keep_refresh=tok["refresh_token"])["access_token"]
