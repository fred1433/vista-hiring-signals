---
name: monday-signals
description: Rebuild the weekly list of Vista by Viewpoint users hiring finance staff, from employer careers pages only, then draft notes for the matched accounts. Use on Monday mornings or when asked to "refresh the Vista list".
---

# Monday signals

1. Run `python -m signals watch` to see the planned reads, then `python -m signals watch --fetch` for the
   employers with a public feed (Greenhouse, Lever). Never open Indeed, SimplyHired, SEEK, Jora, ZipRecruiter
   or LinkedIn: `signals.watch.guard` refuses them, and so do you.
2. Open each "open by hand" page in `data/watchlist.csv` once. For every finance ad, copy into a new
   `data/pages_<date>.json`: the link, the posting date shown (or the relative date, converted with
   `signals.rules.parse_relative`), the HTTP status, and at most two short quotes copied word for word.
3. Run `python -m signals ledger --pages data/pages_<date>.json`. The count must close
   (pages read = matched + hold + excluded). Read every hold and exclusion reason.
4. For each matched account, write the note and two follow-ups in `data/drafts_<date>.json` with only
   `{first_name}` and `{company}` as slots, then run `python -m signals drafts <account> --first-name Test`.
   A draft that names another employer, quotes another ad, or uses a number not in the facts is refused.
5. The person is chosen in Sales Navigator by a human. Only then:
   `python -m signals payload <account> --profile-url <url>` gives the HeyReach body. Nothing is sent.
6. Run `python -m pytest -q` before sharing the list.
