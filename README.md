# Vista hiring signals

Finance job ads that name **Vista by Viewpoint**, read by hand from employer pages on 23 November 2026,
turned into a short list of accounts with the reason for each decision, a LinkedIn note under 200 characters,
two follow-ups, and the body for HeyReach once a person has been chosen in Sales Navigator.

The read found **2 matched accounts, 4 on hold, 9 excluded** (18 pages, the count closes), and 0 in Australia.

```bash
python3 -m venv .venv && .venv/bin/pip install pytest "mcp>=1.2"
.venv/bin/python -m signals ledger                                   # the week's list, with reasons
.venv/bin/python -m signals drafts utilitra --first-name Dana         # note + two follow-ups, validated
.venv/bin/python -m signals payload utilitra --profile-url https://www.linkedin.com/in/<chosen-person>
.venv/bin/python -m signals check "Experience with Viewpoint Vista essential" --title "AP Officer" --posted 13d
.venv/bin/python -m signals watch            # planned Monday reads; add --fetch to read the public feeds
.venv/bin/python -m pytest -q
```

- `data/pages_2026-11-23.json`: every page opened, with link, posting date, HTTP status and short quotes.
- `signals/rules.py`: what counts as Vista (not Windows Vista, Bella Vista, Vista, CA or a company name),
  freshness (14-day window, 30 days expired), relative dates, group duplicates, staffing agencies.
- `signals/drafts.py`: fills the drafts and refuses any sentence that names another employer, quotes another ad,
  borrows a role or a number, or goes over 200 characters.
- `signals/mcp_server.py` and `.mcp.json`: the same rules as MCP tools for Claude Code.
- `.claude/skills/monday-signals/SKILL.md`: the weekly routine.

No job board is read by machine (Indeed, SimplyHired, SEEK, Jora, ZipRecruiter, LinkedIn are refused in code).
No personal data is stored: people are chosen in Sales Navigator, by a person. Nothing is sent from here.
Sending tools like HeyReach act on your LinkedIn account, which LinkedIn's User Agreement does not allow for
automated methods: the risk is the account owner's.

Built by Frederic de Lavenne de Choulot, The AI Pipe.
