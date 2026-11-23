"""Turn the pages read on one day into accounts: matched, on hold, or excluded, with the reason written by code."""
from __future__ import annotations

import json
from collections import OrderedDict
from datetime import date
from pathlib import Path

from . import rules

DATA = Path(__file__).resolve().parent.parent / "data"
DEFAULT_PAGES = DATA / "pages_2026-11-23.json"

STATUS_LABEL = {"matched": "matched", "hold": "on hold", "excluded": "excluded"}

HOLD_TEXT = {
    "group_purchasing": "Posted on The MasTec Companies careers portal: this office sits inside a large group, and who buys software for it cannot be read from the ad.",
    "not_in_current_openings": "The ad page is live but undated, and the role is missing from the employer's own list of current openings.",
    "portal_offline": "The employer's job portal was offline when we tried to read it.",
    "board_only": "The finance ad was seen only on a job board we do not read by machine, and the employer's careers page did not open.",
    "undated": "The ad names Vista but shows no posting date, so its freshness cannot be proven.",
}


def _d(s):
    return date.fromisoformat(s) if s else None


def fmt(d: date) -> str:
    return f"{d.day} {d.strftime('%b')} {d.year}"


def load(path=DEFAULT_PAGES) -> dict:
    return json.loads(Path(path).read_text())


def classify_page(page: dict, read_on: date) -> dict:
    text = " ".join([page.get("title", "")] + page.get("quotes", []) + [page.get("location") or ""])
    posted = _d(page.get("posted"))
    fresh = rules.freshness(posted, read_on)
    labels = rules.vista_mentions(text)
    product_sentences = [q for q in [page.get("title", "")] + page.get("quotes", []) if rules.names_vista(q)]
    if any(s in page["employer"].lower() for s in rules.NEVER_PROSPECT):
        code = "never_prospect"
    elif page.get("hold") in ("portal_offline", "board_only"):
        code = "hold:" + page["hold"]
    elif rules.is_closed(page):
        code = "closed"
    elif page.get("hold"):
        code = "hold:" + page["hold"]
    elif "place" in labels and "product" not in labels:
        code = "vista_is_a_place"
    elif "company_name" in labels and "product" not in labels:
        code = "vista_is_a_name"
    elif "windows" in labels and "product" not in labels:
        code = "windows_vista"
    elif page.get("kind") == "vista_consultancy":
        code = "vista_consultancy"
    elif rules.is_staffing(page["employer"]) or page.get("kind") == "staffing_agency":
        code = "employer_hidden"
    elif not rules.FINANCE_TITLE.search(page.get("title", "")):
        code = "not_finance"
    elif rules.spectrum_only(text):
        code = "spectrum_only"
    elif not product_sentences:
        code = "no_vista"
    elif all(rules.vista_among_alternatives(s) for s in product_sentences):
        code = "vista_one_option"
    elif fresh == "undated":
        code = "hold:undated"
    elif fresh in ("outside_window", "expired", "future"):
        code = fresh
    else:
        code = "migrating_to_vista" if rules.migrating_to_vista(text) else "names_vista"
    return {"id": page["id"], "title": page["title"], "url": page["url"], "posted": page.get("posted"),
            "freshness": fresh, "code": code, "quotes": page.get("quotes", []), "location": page.get("location"),
            "source": page.get("source"), "http": page.get("http"),
            "age_days": (read_on - posted).days if posted else None}


def page_reason(p: dict, employer: str) -> str:
    c = p["code"]
    if c == "closed":
        return f"Closed when read: the page answered {p['http']}" + (" with 'Job Not Found'." if p["http"] == 200 else ".")
    if c in ("outside_window", "expired"):
        return f"Posted {fmt(_d(p['posted']))}, {p['age_days']} days before our read: outside the {rules.WINDOW_DAYS}-day window."
    return {
        "vista_is_a_place": "Here Vista is a place name, not the software.",
        "vista_is_a_name": f"Vista is part of the employer's name ({employer}), not the software.",
        "windows_vista": "Windows Vista, not the construction ERP.",
        "vista_consultancy": "A Vista consultancy hiring for its clients: a peer, not a buyer.",
        "employer_hidden": "A staffing agency listing: the employer is not named.",
        "not_finance": "Not a finance role.",
        "spectrum_only": "Names Viewpoint Spectrum, not Vista.",
        "no_vista": "The ad does not name Vista.",
        "vista_one_option": "Vista appears only as one option among other systems, so the ad does not show they run it.",
        "never_prospect": "Existing Statement Zen relationship: never prospected.",
    }.get(c, c)


def build(data: dict) -> dict:
    read_on = _d(data["read_on"])
    pages = [dict(classify_page(p, read_on), employer=p["employer"]) for p in data["pages"]]
    accounts: "OrderedDict[str, dict]" = OrderedDict()
    for p in pages:
        key = rules.employer_key(p["employer"])
        acc = accounts.setdefault(key, {"id": key, "employer": p["employer"], "pages": []})
        acc["pages"].append(p)
    for acc in accounts.values():
        _settle(acc, read_on)
    order = {"matched": 0, "hold": 1, "excluded": 2}
    rows = sorted(accounts.values(), key=lambda a: (order[a["status"]], -(a["sort_date"] or 0)))
    counts = {s: sum(1 for a in rows if a["status"] == s) for s in order}
    page_counts = {s: sum(len(a["pages"]) for a in rows if a["status"] == s) for s in order}
    proof = {"pages_read": len(pages), "by_status": page_counts,
             "closes": sum(page_counts.values()) == len(pages),
             "merged": sum(len(a["pages"]) - 1 for a in rows)}
    return {"read_on": data["read_on"], "window_days": data.get("window_days", rules.WINDOW_DAYS),
            "accounts": rows, "counts": counts, "proof": proof,
            "also_read": data.get("also_read", []), "australia": data.get("australia", {})}


def _settle(acc: dict, read_on: date) -> None:
    ps = acc["pages"]
    codes = [p["code"] for p in ps]
    dated = [_d(p["posted"]) for p in ps if p["posted"]]
    acc["sort_date"] = max(d.toordinal() for d in dated) if dated else None
    matched = [p for p in ps if p["code"] in ("names_vista", "migrating_to_vista")]
    holds = [c.split(":", 1)[1] for c in codes if c.startswith("hold:")]
    if "never_prospect" in codes:
        acc.update(status="excluded", reason="never_prospect", reason_text=page_reason(ps[0], acc["employer"]))
    elif holds:
        acc.update(status="hold", reason=holds[0], reason_text=HOLD_TEXT[holds[0]])
    elif matched:
        acc.update(status="matched", reason=matched[0]["code"], reason_text=_we_read(acc, matched))
    else:
        first = next((p for p in ps if p["code"] != "closed"), ps[0])
        acc.update(status="excluded", reason=first["code"], reason_text=page_reason(first, acc["employer"]))
    lead = _lead_page(ps)
    acc["lead_page"] = lead["id"]
    acc["location"] = next((p["location"] for p in ps if p.get("location")), None)


def _lead_page(ps):
    open_fin = [p for p in ps if p["code"] != "closed"] or ps
    with_statements = [p for p in open_fin if any("statement" in q.lower() for q in p["quotes"])]
    pool = with_statements or open_fin
    return max(pool, key=lambda p: p["posted"] or "")


def _we_read(acc: dict, matched: list) -> str:
    live = [p for p in acc["pages"] if p["code"] != "closed" and p["freshness"] == "fresh"]
    dates = sorted(_d(p["posted"]) for p in live)
    parts = []
    if len(live) > 1:
        parts.append(f"{len(live)} finance ads posted between {fmt(dates[0])} and {fmt(dates[-1])}.")
    else:
        parts.append(f"One finance ad, posted {fmt(dates[0])}.")
    parts.append("Vista named in: " + ", ".join(p["title"] for p in matched) + ".")
    st = [p["title"] for p in live if any("statement" in q.lower() for q in p["quotes"])]
    if st:
        parts.append("Vendor statements named in: " + ", ".join(st) + ".")
    for p in live:
        for q in p["quotes"]:
            if q.lower().startswith("reports to:"):
                parts.append(f"The {p['title']} reports to the {q.split(':', 1)[1].strip()}.")
    if any(p["code"] == "migrating_to_vista" for p in matched):
        parts.append("The employer is moving to Vista.")
    return " ".join(parts)


def account(ledger: dict, account_id: str) -> dict:
    for a in ledger["accounts"]:
        if a["id"] == account_id:
            return a
    known = ", ".join(a["id"] for a in ledger["accounts"])
    raise KeyError(f"unknown account '{account_id}'. Known accounts: {known}")
