"""python -m signals <command>. Commands: ledger, drafts, payload, check, watch."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date

from . import drafts as D
from . import ledger as L
from . import payload as P
from . import rules, watch


def _ledger(args):
    return L.build(L.load(args.pages))


def cmd_ledger(args):
    led = _ledger(args)
    for status in ("matched", "hold", "excluded"):
        rows = [a for a in led["accounts"] if a["status"] == status]
        print(f"\n{status.upper()} ({len(rows)})")
        for a in rows:
            print(f"  {a['id']:<34} {a['reason_text']}")
    pr = led["proof"]
    b = pr["by_status"]
    print(f"\nPages read on {led['read_on']}: {pr['pages_read']} = {b['matched']} in matched accounts + {b['hold']} on hold + {b['excluded']} excluded"
          f" -> {'closes' if pr['closes'] else 'DOES NOT CLOSE'}")
    print(f"Australia: {led['australia'].get('found', 0)}")
    return 0


def cmd_drafts(args):
    led = _ledger(args)
    acc = L.account(led, args.account)
    if acc["status"] != "matched":
        print(f"{acc['employer']} is {L.STATUS_LABEL[acc['status']]}: {acc['reason_text']} No drafts.", file=sys.stderr)
        return 2
    if not args.first_name:
        d = D.load_drafts()["accounts"][acc["id"]]
        print(f"Templates for {acc['employer']} (fill with --first-name). Note budget left for the first name: "
              f"{D.note_budget(acc['id'], employer=acc['employer'])} characters.\n")
        for k in ("note", "followup_1", "followup_2"):
            print(f"[{k}]\n{d[k]}\n")
        return 0
    out = D.render(acc, led, args.first_name)
    for k, v in out.items():
        extra = f" ({len(v)}/{rules.NOTE_LIMIT})" if k == "note" else ""
        print(f"[{k}]{extra}\n{v}\n")
    return 0


def cmd_payload(args):
    led = _ledger(args)
    acc = L.account(led, args.account)
    print(json.dumps(P.heyreach(acc, args.profile_url, args.campaign_id, args.sender_id), indent=2))
    return 0


def cmd_check(args):
    text = " ".join([args.title or ""] + args.text)
    posted = rules.parse_relative(args.posted, date.today()) if args.posted and not args.posted[:4].isdigit() else (
        date.fromisoformat(args.posted) if args.posted else None)
    page = {"id": "adhoc", "employer": args.employer or "unknown", "title": args.title or "", "url": "", "http": 200,
            "posted": posted.isoformat() if posted else None, "quotes": [" ".join(args.text)], "location": None}
    res = L.classify_page(page, date.today())
    print(json.dumps({"vista_mentions": rules.vista_mentions(text), "code": res["code"], "freshness": res["freshness"],
                      "reason": L.page_reason(res, page["employer"]) if not res["code"].startswith(("names", "migrating")) else "would be listed"}, indent=2))
    return 0


def cmd_watch(args):
    if args.fetch:
        for f in watch.fetch():
            print(f"{f['posted']}  {f['freshness']:<14} {f['employer']}: {f['title']}  {f['url']}")
        return 0
    for p in watch.plan():
        print(f"{p['how']:<20} {p['employer']:<28} {p['url']}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m signals")
    ap.add_argument("--pages", default=str(L.DEFAULT_PAGES), help="pages file (default: the 23 Nov 2026 read)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ledger", help="accounts with status and reason")
    s = sub.add_parser("drafts", help="connection note and two follow-ups for a matched account")
    s.add_argument("account"); s.add_argument("--first-name")
    s = sub.add_parser("payload", help="HeyReach AddLeadsToCampaignV2 body for one chosen person")
    s.add_argument("account"); s.add_argument("--profile-url"); s.add_argument("--campaign-id", type=int); s.add_argument("--sender-id", type=int)
    s = sub.add_parser("check", help="classify one ad text")
    s.add_argument("text", nargs="+"); s.add_argument("--title"); s.add_argument("--employer"); s.add_argument("--posted", help="ISO date or '13d', '5mo ago'")
    s = sub.add_parser("watch", help="Monday run: list planned reads, or --fetch to read the public feeds")
    s.add_argument("--fetch", action="store_true")
    args = ap.parse_args(argv)
    try:
        return {"ledger": cmd_ledger, "drafts": cmd_drafts, "payload": cmd_payload, "check": cmd_check, "watch": cmd_watch}[args.cmd](args)
    except (KeyError, D.DraftError, P.PayloadError, watch.Blocked) as e:
        print(f"error: {e.args[0] if e.args else e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
