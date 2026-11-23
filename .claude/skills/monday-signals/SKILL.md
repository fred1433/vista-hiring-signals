---
name: monday-signals
description: Refresh the list of Vista by Viewpoint users hiring finance staff, from employer careers pages only, then draft notes for the matched accounts. Use when asked to "refresh the Vista list", typically on a Monday.
---

# Monday signals

This is the routine we use to refresh the list. Nothing is scheduled: you run it in Claude Code.

1. Run `python -m signals watch` to see the planned reads, then `python -m signals watch --fetch` for the
   employers with a public feed (Greenhouse, Lever). Each ad found is classified by the same rules as the ledger
   ("keep" or "set aside" with the reason). A feed that fails is reported on its own line and the others are
   still read. Never open Indeed, SimplyHired, SEEK, Jora, ZipRecruiter or LinkedIn: `signals.watch.guard`
   refuses them, and so do you.
2. Open each "open by hand" page in `data/watchlist.csv` once. For every finance ad, copy into a new
   `data/pages_<date>.json`: the link, the posting date shown (or the relative date, converted with
   `signals.rules.parse_relative`; a date read from page metadata goes with `posted_from`), the HTTP status,
   and at most two short quotes copied word for word. A portal error message goes in `portal_message`, never
   in `quotes`.
3. Run `python -m signals ledger --pages data/pages_<date>.json`. The count must close
   (pages read = pages in matched + hold + excluded accounts). Read every hold and exclusion reason.
4. For each matched account, write the note and two follow-ups in `data/drafts_<date>.json` (same date as the
   pages file) with only `{first_name}` and `{company}` as slots, then run
   `python -m signals drafts <account> --first-name Test --pages data/pages_<date>.json`.
   A draft is refused if it holds a quotation not found in that account's ads, names another employer or another
   ad's role (AP read as Accounts Payable), mentions a system, vendor statements, a reporting line or a move to
   Vista the ads do not, gives a number (figures or words) from elsewhere or a percentage, leaves a slot empty,
   or runs over 200 characters (the note).
5. The person is chosen in Sales Navigator by a human. Only then:
   `python -m signals payload <account> --profile-url <url> --first-name <name> --pages data/pages_<date>.json`
   gives the HeyReach body with the checked drafts as custom fields. Nothing is sent.
6. Run `python -m pytest -q` before sharing the list.
