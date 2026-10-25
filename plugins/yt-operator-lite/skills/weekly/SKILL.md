---
name: weekly
description: "Weekly YouTube report computed from the creator's own analytics: last 7 days vs the 7 before, each recent video vs their median at the same age, and one fix. Use for any channel or last-video check-in."
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/yto.py *)
---

# Weekly report

1. Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/yto.py weekly` — add `--lang de|es|pt|ja` when the user writes in that language. Not connected and they want an example: `... weekly --demo`.
2. "Not connected yet" or "sign-in ended" → use the connect skill.
3. Show the report as printed. Then at most 3 sentences in the user's language: what the ONE fix means for this video, written in the channel's voice (`voice` in the profile shown by `yto.py profile`).
4. Offer one next step that matches the fix (retention, ctr, check, plan).

Rules: every number you say must be in the output — never estimate or invent one. Do not re-explain the method; the footnotes do. The pack is read-only and posts nothing.
