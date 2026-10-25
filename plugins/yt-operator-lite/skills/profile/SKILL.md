---
name: profile
description: "Show or update the channel profile every YouTube skill reuses (computed medians, upload gap, best weekdays, voice, capacity, rivals). Use when the user describes the channel, tone, schedule or rivals."
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/yto.py *)
---

# Channel profile

- Show: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/yto.py profile` (`--refresh` recomputes the numbers from a new pull).
- Save what the user tells you, one `--set` per field (lists separated by `|`):
  `... profile --set voice.tone="dry, practical" --set voice.words_to_avoid="insane|hack" --set capacity.uploads_per_week=2 --set capacity.timezone=Europe/Berlin --set rivals="@one|@two"`
  Fields: `language, voice.tone, voice.audience, voice.promise, voice.words_to_use, voice.words_to_avoid, voice.cta, voice.sample_lines, capacity.uploads_per_week, capacity.hours_per_week, capacity.timezone, rivals`.
- First time: ask 4 short questions (who watches, what the channel promises, tone in 3 words, words never to use), save the answers, show the profile.

Rules: never edit `numbers` by hand — only the scripts compute them. Do not invent answers for the user.
