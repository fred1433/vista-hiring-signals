"""Fill a draft for one account and check it against that account's facts before anyone sees it."""
from __future__ import annotations

import json
import re
from pathlib import Path

from . import rules
from .ledger import DATA

DEFAULT_DRAFTS = DATA / "drafts_2026-11-23.json"
PRODUCT = DATA / "product_facts.json"
SLOT = re.compile(r"\{(\w+)\}")
COMMON = {"vista", "new", "network", "business", "links", "priority", "skyline", "robert", "castle", "information",
          "services", "companies", "construction", "contractors", "builders", "company", "group", "fulfillment"}
# A claim about what the hire will do must be backed by the account's own ad text.
CLAIMS = {r"reconcil\w* vendor statements?": "statement", r"vendor statements?": "vendor statement",
          r"procore-to-vista": "procore-to-vista",
          r"\breports? to\b": "reports to", r"\b(moving|migrating|switching) to vista": "to vista"}


# Quotations: double quotes, curly double or single quotes, and straight single quotes that are not apostrophes.
QUOTED = re.compile(r"[\"\u201c]([^\"\u201d]+)[\"\u201d]|\u2018(.+?)\u2019(?!\w)|(?<!\w)'(.+?)'(?!\w)")
# Numbers written in words. "one" is left out: it is also a pronoun ("one of your vendors").
WORDS = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen "
                                    "fourteen fifteen sixteen seventeen eighteen nineteen".split())}
WORDS.update({w: 10 * i for i, w in enumerate("twenty thirty forty fifty sixty seventy eighty ninety".split(), 2)})
WORDS.update({"hundred": 100, "thousand": 1000, "dozen": 12})
NUMBER_WORD = re.compile(r"\b(" + "|".join(w for w in WORDS if w != "one") + r")\b", re.I)
PERCENT = re.compile(r"%|\bper ?cent\b|\bpercentage\b", re.I)


def as_role_text(low: str) -> str:
    """Read AP as Accounts Payable, so 'AP Specialist' is checked as the role 'Accounts Payable Specialist'."""
    return re.sub(r"\bap\b", "accounts payable", low)


class DraftError(ValueError):
    pass


def drafts_path(read_on: str | None = None) -> Path:
    """The drafts belong to one read: data/drafts_<read_on>.json, next to data/pages_<read_on>.json."""
    return DATA / f"drafts_{read_on}.json" if read_on else DEFAULT_DRAFTS


def load_drafts(read_on: str | None = None, path=None) -> dict:
    p = Path(path) if path else drafts_path(read_on)
    if not p.exists():
        raise DraftError(f"no drafts for the read of {read_on}: write {p.relative_to(DATA.parent) if p.is_relative_to(DATA.parent) else p} first")
    return json.loads(p.read_text())


def load_product(path=PRODUCT) -> dict:
    return json.loads(Path(path).read_text())


def fill(template: str, **slots) -> str:
    def sub(m):
        v = slots.get(m.group(1))
        if v is None or not str(v).strip():
            raise DraftError(f"slot '{{{m.group(1)}}}' is empty")
        return str(v).strip()
    return SLOT.sub(sub, template)


def note_length_ok(text: str) -> bool:
    return len(text) <= rules.NOTE_LIMIT


def _allowed_numbers(acc: dict, product: dict) -> set[str]:
    # Posting dates are not allowed as bare numbers: "starts on 17 December" would borrow the 17 of another ad's date.
    nums = set()
    live = [p for p in acc["pages"] if p["code"] != "closed"]
    nums.add(str(len(live)))
    for f in product["facts"].values():
        if isinstance(f["value"], int):
            nums.add(str(f["value"]))
        for w in NUMBER_WORD.findall(f"{f['value']} {f['quote']}"):  # "about ten minutes" on Statement Zen's page
            nums.add(str(WORDS[w.lower()]))
    nums.add(str(product["sender"]["call_minutes"]))
    return nums


def validate(text: str, acc: dict, ledger: dict, product: dict, kind: str = "message") -> list[str]:
    """Return the list of problems; empty means the draft only says what the account's facts say."""
    problems = []
    corpus = " ".join(q for p in acc["pages"] for q in p["quotes"]).lower()
    if SLOT.search(text):
        problems.append("unfilled slot")
    if kind == "note" and not note_length_ok(text):
        problems.append(f"note is {len(text)} characters, over {rules.NOTE_LIMIT}")
    for m in QUOTED.finditer(text):
        q = next(g for g in m.groups() if g is not None)
        body = re.sub(r"(\u2026|\.\.\.)\s*$", "", q.strip())  # a quotation cut short with an ellipsis
        if body.lower() not in corpus:
            problems.append(f"quote not in this account's ads: {q!r}")
    allowed = _allowed_numbers(acc, product)
    for n in re.findall(r"\d[\d,]*", text):
        if n.replace(",", "") not in allowed:
            problems.append(f"number not in this account's facts: {n}")
    for w in NUMBER_WORD.findall(text):
        if str(WORDS[w.lower()]) not in allowed:
            problems.append(f"number not in this account's facts: {w}")
    if PERCENT.search(text):
        problems.append("percentage: no percentage is in this account's facts or on Statement Zen's page")
    low = text.lower()
    for other in ledger["accounts"]:
        if other["id"] == acc["id"]:
            continue
        names = {other["employer"].lower()}
        first = other["employer"].split()[0].lower()
        if first not in COMMON and len(first) > 3:
            names.add(first)
        for n in names:
            if re.search(rf"\b{re.escape(n)}\b", low):
                problems.append(f"names another employer: {other['employer']}")
                break
    roles = as_role_text(low)
    own_titles = {as_role_text(p["title"].lower()) for p in acc["pages"]}
    all_titles = {as_role_text(p["title"].lower()): p["title"] for o in ledger["accounts"] for p in o["pages"] if len(p["title"]) > 12}
    for t, shown in all_titles.items():
        if t in roles and t not in own_titles and not any(t in o and o in roles for o in own_titles):
            problems.append(f"role taken from another ad: {shown}")
    for erp in rules.OTHER_ERPS + ["procore", "pvault"]:
        if re.search(rf"\b{re.escape(erp)}\b", low) and erp not in corpus:
            problems.append(f"system not in this account's ads: {erp}")
    for pat, need in CLAIMS.items():
        if re.search(pat, low) and need not in corpus:
            problems.append(f"claim not backed by this account's ads: {pat}")
    return sorted(set(problems))


def render(acc: dict, ledger: dict, first_name: str, drafts=None, product=None) -> dict:
    drafts = drafts or load_drafts(ledger.get("read_on"))
    product = product or load_product()
    d = drafts["accounts"].get(acc["id"])
    if d is None:
        raise DraftError(f"no drafts for '{acc['id']}': drafts exist only for matched accounts")
    out = {}
    for kind in ("note", "followup_1", "followup_2"):
        text = fill(d[kind], first_name=first_name, company=acc["employer"])
        problems = validate(text, acc, ledger, product, kind="note" if kind == "note" else "message")
        if problems:
            raise DraftError(f"{kind}: " + "; ".join(problems))
        out[kind] = text
    return out


def note_budget(acc_id: str, drafts=None, employer: str = "", read_on: str | None = None) -> int:
    """Characters left for the first name once the company is filled in."""
    drafts = drafts or load_drafts(read_on)
    t = drafts["accounts"][acc_id]["note"].replace("{company}", employer)
    return rules.NOTE_LIMIT - len(t.replace("{first_name}", ""))
