# Vista hiring signals

Finance job ads that name **Vista by Viewpoint**, read by hand from employer pages on 23 November 2026,
turned into a short list of accounts with the reason for each decision, a LinkedIn note under 200 characters,
two follow-ups, and the body for HeyReach once a person has been chosen in Sales Navigator.

The read: **19 pages, 15 accounts**. 2 accounts matched (5 pages), 3 on hold (4 pages), 10 excluded (10 pages);
both columns add up. No Australian match in the sources checked.

```bash
python3 -m venv .venv && .venv/bin/pip install pytest "mcp>=1.2"
.venv/bin/python -m signals ledger                                   # the list, with reasons
.venv/bin/python -m signals drafts utilitra --first-name Dana         # note + two follow-ups, validated
.venv/bin/python -m signals payload utilitra --profile-url https://www.linkedin.com/in/<chosen-person> --first-name Dana
.venv/bin/python -m signals check "Experience with Viewpoint Vista essential" --title "AP Officer" --posted 13d
.venv/bin/python -m signals watch            # planned reads; add --fetch to read the public feeds
.venv/bin/python -m pytest -q
```

`--pages data/pages_<date>.json` works before or after the command; the drafts are read from
`data/drafts_<date>.json` for the same date.

- `data/pages_2026-11-23.json`: every page opened, with link, posting date, HTTP status and short quotes.
- `signals/rules.py`: what counts as Vista (not Windows Vista, Bella Vista, Vista, CA or a company name),
  freshness (14-day window, 30 days expired), relative dates, group duplicates, staffing agencies.
- `signals/drafts.py`: fills the drafts and refuses a draft with a quotation (double or single quotes) not found
  in that account's ads; another employer or another ad's role (AP is read as Accounts Payable); a system, vendor
  statements, a reporting line or a move to Vista that the account's ads do not mention; a number, in figures or
  in words ("one" aside), that is neither the account's count of ads nor on Statement Zen's page, or any
  percentage; an empty slot; a note over 200 characters. It does not check what is said about Statement Zen
  beyond the numbers.
- `signals/watch.py`: the Greenhouse and Lever feeds of watched employers, classified by the same rules as the
  ledger; a feed that fails is reported and the others are still read.
- `tests/test_page.py`: the page's copy buttons in Chromium, including a clipboard that refuses (the text is then
  shown selected, never "Copied"). The page is built in `site/` by `build.py` and published, not kept here, so this
  test skips without it or without `pip install playwright`.
- `signals/mcp_server.py` and `.mcp.json`: the same rules as MCP tools for Claude Code.
- `.claude/skills/monday-signals/SKILL.md`: the Claude Code skill we use to refresh the list. Nothing is scheduled.

No job board is read by machine (Indeed, SimplyHired, SEEK, Jora, ZipRecruiter, LinkedIn are refused in code).
No personal data is stored: people are chosen in Sales Navigator, by a person. Nothing is sent from here.
Sending tools like HeyReach act on your LinkedIn account, which LinkedIn's User Agreement does not allow for
automated methods: the risk is the account owner's.

Built by Frederic de Lavenne de Choulot, The AI Pipe.
