import json
import re

from signals import ledger as L

LED = L.build(L.load())


def test_real_counts_of_the_23_november_read():
    assert LED["counts"] == {"matched": 2, "hold": 3, "excluded": 10}
    assert LED["australia"]["found"] == 0


def test_the_count_closes_like_a_statement():
    pr = LED["proof"]
    assert pr["closes"] and pr["pages_read"] == 19 and pr["accounts"] == 15
    assert sum(pr["by_status"].values()) == 19
    assert pr["by_status"] == {"matched": 5, "hold": 4, "excluded": 10}


def test_one_employer_seen_through_several_ads_appears_once():
    ids = [a["id"] for a in LED["accounts"]]
    assert len(ids) == len(set(ids))
    util = L.account(LED, "utilitra")
    assert len(util["pages"]) == 4 and util["status"] == "matched"
    assert util["reason_text"].startswith("4 finance ads posted between 9 Nov 2026 and 20 Nov 2026.")
    intern = next(p for p in util["pages"] if p["id"] == "utilitra-intern")
    assert intern["code"] == "names_vista" and intern["quotes"] == ["Knowledge of Vista by Viewpoint beneficial, but not expected"]
    assert len(L.account(LED, "mastec")["pages"]) == 2


def test_lead_page_is_the_statement_ad():
    assert L.account(LED, "utilitra")["lead_page"] == "utilitra-ap"


def test_every_page_keeps_link_date_and_status():
    raw = L.load()
    for p in raw["pages"]:
        assert p["url"].startswith("https://")
        assert "http" in p
    assert raw["read_on"] == "2026-11-23"


def test_quotes_are_short_extracts():
    for p in L.load()["pages"]:
        for q in p["quotes"]:
            assert len(q) <= 160, q


def test_no_personal_data_in_published_files():
    for name in ("pages_2026-11-23.json", "drafts_2026-11-23.json", "product_facts.json", "watchlist.csv"):
        text = (L.DATA / name).read_text()
        assert not re.search(r"linkedin\.com/in/", text), name
        assert not re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text), name


def test_matched_accounts_are_fresh_and_name_vista():
    for a in LED["accounts"]:
        if a["status"] == "matched":
            assert any(p["code"] in ("names_vista", "migrating_to_vista") and p["freshness"] == "fresh" for p in a["pages"])


def test_rodan_is_excluded_published_in_september_and_gone_from_openings():
    rodan = L.account(LED, "rodan-builders")
    assert rodan["status"] == "excluded"
    assert rodan["reason_text"] == "Published 10 Sep 2026, 74 days before our read, and no longer in their current openings."


def test_a_portal_outage_message_is_not_an_ad_quote():
    penhall = L.account(LED, "penhall")
    assert penhall["status"] == "hold" and penhall["reason"] == "portal_offline"
    page = penhall["pages"][0]
    assert page["quotes"] == [] and "offline" in page["portal_message"]
    assert L.page_reason(page, penhall["employer"]) == L.HOLD_TEXT["portal_offline"]


def test_the_window_holds_for_matched_accounts_only():
    for a in LED["accounts"]:
        if a["status"] == "matched":
            live = [p for p in a["pages"] if p["code"] != "closed"]
            assert all(p["posted"] >= "2026-11-09" for p in live)
