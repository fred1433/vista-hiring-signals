"""The Monday run: read the careers feeds of employers already known to run Vista, never a job board.
Greenhouse and Lever publish one public feed per employer; other employers are listed for a human to open."""
from __future__ import annotations

import csv
import json
import re
import urllib.request
import urllib.robotparser
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from . import rules
from .ledger import DATA

WATCHLIST = DATA / "watchlist.csv"
BLOCKED = ("indeed.", "simplyhired.", "seek.com", "jora.com", "ziprecruiter.", "linkedin.com", "glassdoor.", "careerone.")
UA = "vista-signals/0.1 (careers feed reader)"


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


def fetch(rows=None, today: date | None = None) -> list[dict]:
    """Read each automatic feed once; return finance ads that name Vista, with their posting date."""
    today = today or date.today()
    found = []
    for r in rows or load_watchlist():
        if r["kind"] not in ("greenhouse", "lever"):
            continue
        data = _get(feed_url(r))
        jobs = data["jobs"] if r["kind"] == "greenhouse" else data
        for j in jobs:
            if r["kind"] == "greenhouse":
                title, text, url = j["title"], re.sub(r"<[^>]+>", " ", j.get("content", "")), j["absolute_url"]
                posted = (j.get("first_published") or j.get("updated_at") or "")[:10]
            else:
                title, url = j["text"], j["hostedUrl"]
                text = (j.get("descriptionPlain") or "") + " " + (j.get("additionalPlain") or "") + " " + " ".join(re.sub(r"<[^>]+>", " ", l.get("content", "")) for l in j.get("lists", []))
                posted = datetime.fromtimestamp(j["createdAt"] / 1000, tz=timezone.utc).date().isoformat()
            if not rules.FINANCE_TITLE.search(title) or not rules.names_vista(text):
                continue
            fresh = rules.freshness(date.fromisoformat(posted) if posted else None, today)
            found.append({"employer": r["employer"], "title": title, "url": url, "posted": posted, "freshness": fresh})
    return found
