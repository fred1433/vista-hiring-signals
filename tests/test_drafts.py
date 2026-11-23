import pytest

from signals import drafts as D
from signals import ledger as L
from signals import payload as P
from signals import rules

LED = L.build(L.load())
PRODUCT = D.load_product()
UTIL = L.account(LED, "utilitra")
CAHILL = L.account(LED, "cahill-contractors")


@pytest.mark.parametrize("acc", ["utilitra", "cahill-contractors"])
def test_drafts_pass_their_own_validator(acc):
    out = D.render(L.account(LED, acc), LED, "Alexandria")
    assert len(out["note"]) <= rules.NOTE_LIMIT


def test_note_fits_even_with_a_long_first_name():
    for acc in ("utilitra", "cahill-contractors"):
        a = L.account(LED, acc)
        assert D.note_budget(acc, employer=a["employer"]) >= 15


def test_limit_is_200_not_201():
    assert D.note_length_ok("x" * 200)
    assert not D.note_length_ok("x" * 201)
    assert D.note_length_ok("’" * 200)
    assert not D.note_length_ok("’" * 201)


def test_empty_slot_is_refused():
    with pytest.raises(D.DraftError):
        D.fill("Hi {first_name}", first_name="  ")
    with pytest.raises(D.DraftError):
        D.fill("Hi {first_name} at {company}", first_name="Sam")


def test_note_too_long_after_substitution_is_refused():
    long_name = "Maximiliana-Alexandrina-Konstantinopolous"
    with pytest.raises(D.DraftError):
        D.render(UTIL, LED, long_name * 2)


# Plausible wrong sentences, replayed against the validator.
WRONG = [
    ("another employer's name", UTIL, "Thanks Sam. Like Cahill Contractors, you are moving invoices into Vista."),
    ("short employer name", UTIL, "Thanks Sam, I saw Rodan is hiring too."),
    ("quote from another account", UTIL, "Your ad says \"managing the Procore-to-Vista ERP sync and integration\"."),
    ("role from another account", UTIL, "I saw Utilitra is hiring a Senior Project Accountant."),
    ("reason lent to the wrong account", CAHILL, "I saw Cahill Contractors is hiring someone to reconcile vendor statements."),
    ("number taken elsewhere", UTIL, "The first 50 statements each month are free."),
    ("two orders added together", UTIL, "Utilitra has 4 finance roles open right now."),
    ("system not in the ad", CAHILL, "Since you run NetSuite next to Vista, this may help."),
    ("reporting line not in the ad", CAHILL, "Your new hire reports to the AP Supervisor."),
    ("percentage claim", UTIL, "It saves 80% of the time."),
]


@pytest.mark.parametrize("why,acc,text", WRONG, ids=[w[0] for w in WRONG])
def test_validator_catches_plausible_wrong_sentences(why, acc, text):
    assert D.validate(text, acc, LED, PRODUCT), why


def test_validator_accepts_true_sentences():
    ok = "I saw Utilitra is adding an Accounts Payable Specialist; the first 25 statements each month are free."
    assert D.validate(ok, UTIL, LED, PRODUCT) == []


def test_no_drafts_for_accounts_on_hold():
    with pytest.raises(D.DraftError):
        D.render(L.account(LED, "rodan-builders"), LED, "Sam")


def test_payload_needs_the_person_chosen_in_sales_navigator():
    with pytest.raises(P.PayloadError):
        P.heyreach(UTIL, None)
    with pytest.raises(P.PayloadError):
        P.heyreach(UTIL, "https://example.com/someone")
    body = P.heyreach(UTIL, "https://www.linkedin.com/in/example-person")
    fields = body["accountLeadPairs"][0]["lead"]["customUserFields"]
    assert all(P.FIELD_NAME.match(f["name"]) for f in fields)
    assert {f["name"] for f in fields} >= {"signal_quote", "ad_date", "ad_url"}


def test_payload_refused_for_held_or_excluded_accounts():
    with pytest.raises(P.PayloadError):
        P.heyreach(L.account(LED, "mastec"), "https://www.linkedin.com/in/example-person")
