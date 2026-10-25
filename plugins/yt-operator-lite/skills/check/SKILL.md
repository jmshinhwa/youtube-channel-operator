---
name: check
description: "Check a YouTube title, description and tags against YouTube's limits and, with Pro, against the creator's own best titles and search terms. Use for any draft title/description/tags."
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/yto.py *) Write
---

# Upload text check

1. Save the description (if any) to a temporary file, then run
   `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/yto.py check --title "<title>" --description-file <file> --tags "a,b,c"`.
2. Report the issues it lists. If the user wants alternatives, write up to 3 titles in the channel's voice that fix them, and run `check` on each before showing it.

Rules: limits and counts come from the script, never from memory. Do not promise views or rankings.
