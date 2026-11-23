"""The Monday run: read the careers feeds of employers already known to run Vista, never a job board.
Greenhouse and Lever publish one public feed per employer; other employers are listed for a human to open.
Each ad found goes through the same classify_page as the ledger, so a feed never keeps what the ledger would set aside."""
from __future__ import annotations

import csv
import html
import json
import re
import urllib.error
import urllib.request
import urllib.robotparser
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from . import rules
from .ledger import DATA, classify_page, page_reason

WATCHLIST = DATA / "watchlist.csv"
BLOCKED = ("indeed.", "simplyhired.", "seek.com", "jora.com", "ziprecruiter.", "linkedin.com", "glassdoor.", "careerone.")
UA = "vista-signals/0.1 (careers feed reader)"
KEEP = ("names_vista", "migrating_to_vista")


class Blocked(ValueError):
    pass


def feed_url(row: dict) -> str:
    if row["kind"] == "greenhouse":
        return f"https://boards-api.greenhouse.io/v1/boards/{row['target']}/jobs?content=true"
    if row["kind"] == "lever":
        return f"https://api.lever.co/v0/postings/{row['target']}?mode=json"
    return row["target"]


def guard(url: str) -> None:
    host = urlparse(url).netloc.lower()
    if any(b in host for b in BLOCKED):
        raise Blocked(f"refused: {host} is a job board whose terms forbid automated reading")


def load_watchlist(path=WATCHLIST) -> list[dict]:
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def plan(rows=None) -> list[dict]:
    out = []
    for r in rows or load_watchlist():
        url = feed_url(r)
        try:
            guard(url)
            how = "read automatically" if r["kind"] in ("greenhouse", "lever") else "open by hand"
        except Blocked as e:
            how = str(e)
        out.append({"employer": r["employer"], "url": url, "how": how, "why_watched": r["why_watched"]})
    return out


def robots_allows(url: str) -> bool:
    u = urlparse(url)
    rp = urllib.robotparser.RobotFileParser(f"{u.scheme}://{u.netloc}/robots.txt")
    try:
        rp.read()
    except Exception:
        return True
    return rp.can_fetch(UA, url)


def _get(url: str):
    guard(url)
    if not robots_allows(url):
        raise Blocked(f"refused by robots.txt: {url}")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def strip_tags(s: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def lever_text(j: dict) -> str:
    """Some Lever boards leave descriptionPlain empty and keep the ad only in the HTML description."""
    body = j.get("descriptionPlain") or strip_tags(j.get("description", ""))
    extra = j.get("additionalPlain") or strip_tags(j.get("additional", ""))
    lists = " ".join(strip_tags(l.get("text", "")) + " " + strip_tags(l.get("content", "")) for l in j.get("lists", []))
    return " ".join([body, extra, lists])


def vista_sentences(text: str, limit: int = 3) -> list[str]:
    parts = re.split(r"(?<=[.!?;])\s+|\n|•", text)
    return [p.strip()[:300] for p in parts if re.search(r"vista", p, re.I)][:limit]


def _ads(r: dict, data) -> list[dict]:
    out = []
    jobs = data["jobs"] if r["kind"] == "greenhouse" else data
    for j in jobs:
        if r["kind"] == "greenhouse":
            title, text, url = j["title"], strip_tags(html.unescape(j.get("content", ""))), j["absolute_url"]
            posted = (j.get("first_published") or j.get("updated_at") or "")[:10]
        else:
            title, url, text = j["text"], j["hostedUrl"], lever_text(j)
            posted = datetime.fromtimestamp(j["createdAt"] / 1000, tz=timezone.utc).date().isoformat()
        if rules.FINANCE_TITLE.search(title) and rules.names_vista(text):
            out.append({"title": title, "url": url, "posted": posted or None, "quotes": vista_sentences(text)})
    return out


def fetch(rows=None, today: date | None = None, get=None) -> dict:
    """Read each automatic feed once. A feed that fails is noted and the others are still read.
    Returns {"ads": [...], "errors": [...]}; every ad carries the ledger's code, keep flag and reason."""
    today = today or date.today()
    get = get or _get
    ads, errors = [], []
    for r in rows or load_watchlist():
        if r["kind"] not in ("greenhouse", "lever"):
            continue
        try:
            data = get(feed_url(r))
            found = _ads(r, data)
        except (urllib.error.URLError, OSError, ValueError, KeyError, TypeError) as e:
            errors.append({"employer": r["employer"], "url": feed_url(r), "error": f"{type(e).__name__}: {e}"})
            continue
        for a in found:
            page = {"id": a["url"], "employer": r["employer"], "http": 200, "location": None, **a}
            res = classify_page(page, today)
            keep = res["code"] in KEEP
            ads.append({"employer": r["employer"], "title": a["title"], "url": a["url"], "posted": a["posted"],
                        "freshness": res["freshness"], "code": res["code"], "keep": keep,
                        "reason": "names Vista, inside the window" if keep else page_reason(res, r["employer"])})
    return {"ads": ads, "errors": errors}
