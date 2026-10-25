---
name: chapters
description: "YouTube chapters from an .srt/.vtt transcript, or a check of written chapters against YouTube's rules (00:00 first, 3+, ascending, 10 s each)."
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/yto.py *) Write
---

# Chapters

1. From a transcript: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/yto.py chapters --transcript <file.srt|.vtt>` (optional `--count N`, `--duration SECONDS`).
2. Name each proposed start from its text: 2–5 words, in the video's language and the channel's voice. Keep the times exactly.
3. Write the list to a file (one `M:SS Title` per line) and run `... chapters --check <file>`. Fix anything it reports and check again.
4. Give the final block ready to paste into the description.

Rules: never move a time the script gave without re-running `--check`.
