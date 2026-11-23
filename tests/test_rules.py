from datetime import date

import pytest

from signals import rules
from signals.ledger import classify_page

READ = date(2026, 11, 23)


def page(title, text, employer="Acme Civil", posted="2026-11-20", http=200, **kw):
    return dict({"id": "t", "employer": employer, "title": title, "url": "", "http": http, "posted": posted,
                 "quotes": [text], "location": None}, **kw)


@pytest.mark.parametrize("text,label", [
    ("Experience with Viewpoint Vista essential", "product"),
    ("Vista by Viewpoint experience required", "product"),
    ("Maintain vendor records in Vista by Viewpoint", "product"),
    ("Managing the Procore-to-Vista ERP sync", "product"),
    ("Proficient in Windows Vista and Office", "windows"),
    ("Office based in Bella Vista NSW", "place"),
    ("Accounts Payable role in Chula Vista", "place"),
    ("Construction Accounting Vista, CA onsite", "place"),
    ("Accounts Payable Specialist - Vista Fulfillment Group", "company_name"),
    ("Vista Equity portfolio company", "company_name"),
])
def test_vista_labels(text, label):
    assert label in rules.vista_mentions(text)


def test_windows_vista_does_not_enter():
    assert classify_page(page("Accounts Payable Officer", "Must know Windows Vista"), READ)["code"] == "windows_vista"


def test_bella_vista_does_not_enter():
    assert classify_page(page("Accounts Payable Officer", "Located in Bella Vista NSW, close to transport"), READ)["code"] == "vista_is_a_place"


def test_vista_in_a_list_of_examples_is_not_a_user():
    t = "Experience with Sage 300 CRE, Viewpoint Vista, Foundation or similar"
    assert rules.vista_among_alternatives(t)
    assert classify_page(page("AP Manager", t), READ)["code"] == "vista_one_option"


def test_vista_with_procore_is_not_a_list_of_alternatives():
    assert not rules.vista_among_alternatives("Experience with Viewpoint Vista and Procore preferred.")


def test_spectrum_is_not_vista():
    assert classify_page(page("Staff Accountant", "Experience with Viewpoint Spectrum required"), READ)["code"] == "spectrum_only"


def test_moving_to_vista_keeps_its_own_label():
    t = "We move from QuickBooks to Vista on January 1; review all statements against the vendor account in Viewpoint"
    assert classify_page(page("AP Coordinator", t), READ)["code"] == "migrating_to_vista"


def test_staffing_agency_hides_employer():
    assert classify_page(page("AP Specialist", "Vista by Viewpoint required", employer="Robert Half"), READ)["code"] == "employer_hidden"


def test_consultancy_is_a_peer():
    p = page("Software Consultant", "support of Trimble Viewpoint Vista for our clients", kind="vista_consultancy")
    assert classify_page(p, READ)["code"] == "vista_consultancy"


@pytest.mark.parametrize("posted,expected", [
    ("2026-11-09", "fresh"), ("2026-11-08", "outside_window"), ("2026-10-24", "outside_window"),
    ("2026-10-23", "expired"), (None, "undated"),
])
def test_freshness_edges(posted, expected):
    assert rules.freshness(date.fromisoformat(posted) if posted else None, READ) == expected


def test_old_ad_is_not_listed():
    assert classify_page(page("AP Specialist", "Vista by Viewpoint", posted="2026-10-01"), READ)["code"] == "expired"


def test_closed_ad_is_removed():
    assert classify_page(page("AP Specialist", "Vista by Viewpoint", http=410), READ)["code"] == "closed"
    assert classify_page(page("AP Specialist", "Vista by Viewpoint", closed_marker="Job Not Found"), READ)["code"] == "closed"


@pytest.mark.parametrize("raw,expected", [
    ("5mo ago", date(2026, 6, 26)), ("13d", date(2026, 11, 10)), ("3 weeks ago", date(2026, 11, 2)),
    ("yesterday", date(2026, 11, 22)), ("today", READ), ("30+ days ago", date(2026, 10, 24)), ("soon", None),
    ("2 hrs ago", READ), ("2 wks ago", date(2026, 11, 9)), ("a month ago", date(2026, 10, 24)), ("an hour ago", READ),
])
def test_relative_dates(raw, expected):
    assert rules.parse_relative(raw, READ) == expected


def test_entities_of_one_group_share_a_key():
    assert rules.employer_key("CEI Services") == rules.employer_key("MasTec") == "mastec"
    assert rules.employer_key("Penhall Company") == rules.employer_key("Penhall Co.") == "penhall"


def test_existing_customer_is_never_prospected():
    p = page("Accounts Payable Officer", "Vista by Viewpoint experience", employer="Shadforth Civil Engineering")
    assert classify_page(p, READ)["code"] == "never_prospect"
