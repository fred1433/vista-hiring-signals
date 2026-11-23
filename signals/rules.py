"""Rules applied to one job ad. Pure functions, no network."""
from __future__ import annotations

import re
from datetime import date, timedelta

WINDOW_DAYS = 14      # the list shows ads posted in the last 14 days
EXPIRED_DAYS = 30     # older than this, the ad is treated as expired
NOTE_LIMIT = 200      # LinkedIn help article 46662: "Each message can be up to 200 characters."

# Other accounting systems. Procore and pVault are not ledgers, so they never make Vista "one option among several".
OTHER_ERPS = ["netsuite", "sage", "foundation", "quickbooks", "cmic", "acumatica", "spectrum", "oracle",
              "jd edwards", "dynamics", "business central", "myob", "xero", "ukg", "adp", "timberline", "sap", "workday"]
PLACES_BEFORE = ["bella", "chula", "buena", "mountain", "monte", "sierra", "linda", "bonita", "alta", "rancho", "costa"]
CITY_AFTER = re.compile(r"^\s*,?\s*(ca|california|nsw|qld|vic|wa|fl|tx|az|co)\b", re.I)
COMPANY_AFTER = re.compile(r"^\s+(fulfillment|equity|group|outdoor|health|homes|realty|bank|capital|partners|logistics)\b", re.I)
VIEWPOINT_NEAR = re.compile(r"viewpoint|trimble|\berp\b|vista\s+web|procore-to-vista|in\s+vista\b", re.I)
MIGRATION = re.compile(r"\b(mov\w*|migrat\w*|transition\w*|switch\w*|convert\w*|implement\w*)\b[^.]{0,60}\bto\s+(viewpoint\s+)?vista\b", re.I)
FINANCE_TITLE = re.compile(r"account|payable|receivable|controller|finance|bookkeep|payroll|billing|\bap\b|\bcfo\b", re.I)
STAFFING = ["robert half", "western work force", "beacon hill", "michael page", "gpac", "northpoint search", "thinkingahead", "ledgent", "lhh"]
NEVER_PROSPECT = ["shadforth"]  # Statement Zen grew out of work with this client: never on a prospect list


def vista_mentions(text: str) -> list[str]:
    """Label each 'vista' in the text: product, place, windows, company_name, or unclear."""
    out = []
    for m in re.finditer(r"vista", text, re.I):
        before = text[max(0, m.start() - 30):m.start()].lower()
        after = text[m.end():m.end() + 40]
        window = text[max(0, m.start() - 40):m.end() + 40]
        if re.search(r"windows\s*$", before):
            out.append("windows")
        elif any(re.search(rf"\b{p}\s*$", before) for p in PLACES_BEFORE) or CITY_AFTER.match(after):
            out.append("place")
        elif COMPANY_AFTER.match(after):
            out.append("company_name")
        elif VIEWPOINT_NEAR.search(window):
            out.append("product")
        else:
            out.append("unclear")
    return out


def names_vista(text: str) -> bool:
    labels = vista_mentions(text)
    return "product" in labels or (bool(MIGRATION.search(text)) and "place" not in labels and "windows" not in labels)


def vista_among_alternatives(sentence: str) -> bool:
    """True when the sentence offers Vista as one choice among other ledgers ('Vista, NetSuite, or similar')."""
    if not names_vista(sentence):
        return False
    low = sentence.lower()
    others = [e for e in OTHER_ERPS if re.search(rf"\b{re.escape(e)}\b", low)]
    return bool(others) and bool(re.search(r"\bor\b|similar|comparable|equivalent|e\.g\.", low))


def migrating_to_vista(text: str) -> bool:
    return bool(MIGRATION.search(text))


def spectrum_only(text: str) -> bool:
    low = text.lower()
    return "spectrum" in low and not names_vista(text)


def freshness(posted: date | None, read_on: date) -> str:
    if posted is None:
        return "undated"
    age = (read_on - posted).days
    if age < 0:
        return "future"
    if age <= WINDOW_DAYS:
        return "fresh"
    if age <= EXPIRED_DAYS:
        return "outside_window"
    return "expired"


_REL = re.compile(r"(?P<n>\d+)\s*\+?\s*(?P<u>mo|month|months|d|day|days|w|wk|week|weeks|h|hr|hours?)\b", re.I)


def parse_relative(raw: str, read_on: date) -> date | None:
    """'5mo ago', '13d', '3 weeks ago', 'yesterday', 'today' -> a date counted back from the read date.
    A month counts as 30 days. Returns None when nothing can be read."""
    s = raw.strip().lower()
    if s in ("today", "just posted", "new"):
        return read_on
    if s == "yesterday":
        return read_on - timedelta(days=1)
    m = _REL.search(s)
    if not m:
        return None
    n, u = int(m.group("n")), m.group("u").lower()
    if u.startswith("mo"):
        return read_on - timedelta(days=30 * n)
    if u.startswith("w"):
        return read_on - timedelta(weeks=n)
    if u.startswith("h"):
        return read_on
    return read_on - timedelta(days=n)


_SUFFIX = re.compile(r"\b(inc|llc|ltd|pty|co|corp|corporation|company|companies|group|the)\b\.?", re.I)
GROUPS = {"cei services": "mastec", "fnf construction": "mastec", "mastec": "mastec", "the mastec companies": "mastec"}


def employer_key(name: str) -> str:
    low = name.lower().strip()
    if low in GROUPS:
        return GROUPS[low]
    k = _SUFFIX.sub(" ", low)
    k = re.sub(r"[^a-z0-9]+", "-", k).strip("-")
    return GROUPS.get(k.replace("-", " "), k)


def is_staffing(employer: str) -> bool:
    low = employer.lower()
    return any(s in low for s in STAFFING) or "confidential" in low


def is_closed(page: dict) -> bool:
    return page.get("http") != 200 or bool(page.get("closed_marker"))
