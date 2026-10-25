---
name: connect
description: "Connect the creator's own YouTube channel (read-only Google sign-in with their own OAuth client) or show a demo report first. Use for setup, or when a yt-operator command says not connected / sign-in ended."
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/yto.py *)
---

# Connect

1. Not connected yet and the user wants to see what they get: run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/yto.py demo` and show it (it is a bundled sample channel — say so).
2. Ask for the path of their OAuth client JSON (type **Desktop app**). If they have none, read `${CLAUDE_PLUGIN_ROOT}/docs/SETUP.md` and walk them through it one step at a time (5 steps).
3. Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/yto.py connect --client <path>`. A browser opens; they sign in with the channel's Google account. If the session is remote (no browser on this machine), use `--manual`, show the printed address, and pass the address they paste back with `--paste "<address>"`.
4. Pro key from the purchase: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/yto.py licence <KEY>` (only the key goes to getreadystack.com).
5. When it prints `Connected: <channel>`, run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/yto.py profile --refresh` and then offer the weekly report.

Rules: never ask for or print the client secret or tokens; never commit the JSON file. The pack is read-only — it cannot upload, edit, comment or delete.
