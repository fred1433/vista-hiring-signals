"""The Monday refresh: feeds that fail, Lever boards with HTML-only text, and the same filter as the ledger."""
import json
import urllib.error
from datetime import date

from signals import watch
from signals.__main__ import main

TODAY = date(2026, 11, 23)
CREATED = 1795119687319  # 19 Nov 2026, as in the Network Connex feed


def lever_job(title, plain="", html="", created=CREATED):
    return {"text": title, "hostedUrl": "https://jobs.lever.co/x/1", "createdAt": created,
            "descriptionPlain": plain, "description": html, "lists": []}


def test_lever_reads_the_html_description_when_the_plain_text_is_empty():
    job = lever_job("Assistant Controller", html="<p>Experience with <b>Viewpoint Vista</b> required.</p>")
    rows = [{"employer": "Acme Civil", "kind": "lever", "target": "acme", "why_watched": ""}]
    res = watch.fetch(rows, TODAY, get=lambda url: [job])
    assert [a["title"] for a in res["ads"]] == ["Assistant Controller"]
    assert res["ads"][0]["keep"] and res["ads"][0]["code"] == "names_vista"


def test_a_dead_feed_is_noted_and_the_others_are_still_read():
    rows = [{"employer": "Gone Co", "kind": "greenhouse", "target": "gone", "why_watched": ""},
            {"employer": "Acme Civil", "kind": "lever", "target": "acme", "why_watched": ""}]

    def get(url):
        if "gone" in url:
            raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)
        return [lever_job("AP Specialist", plain="Vista by Viewpoint experience required.")]
    res = watch.fetch(rows, TODAY, get=get)
    assert len(res["errors"]) == 1 and "404" in res["errors"][0]["error"]
    assert [a["employer"] for a in res["ads"]] == ["Acme Civil"]


def test_fetch_sets_aside_what_the_ledger_sets_aside():
    skyline = lever_job("Payroll Specialist", plain="Experience with payroll and ERP software (Vista by Viewpoint, Foundation, "
                        "Sage, UKG, ADP, or similar systems preferred).", created=1789052400000)  # 10 Sep 2026
    rows = [{"employer": "Skyline Construction", "kind": "lever", "target": "s", "why_watched": ""}]
    ad = watch.fetch(rows, TODAY, get=lambda url: [skyline])["ads"][0]
    assert not ad["keep"] and ad["code"] == "vista_one_option"


def test_greenhouse_content_is_unescaped_before_reading():
    gh = {"jobs": [{"title": "Senior Project Accountant", "absolute_url": "https://job-boards.greenhouse.io/x/jobs/1",
                    "first_published": "2026-11-11T00:00:00Z",
                    "content": "&lt;p&gt;Managing the Procore-to-Vista ERP sync.&lt;/p&gt;"}]}
    rows = [{"employer": "Acme Civil", "kind": "greenhouse", "target": "acme", "why_watched": ""}]
    ad = watch.fetch(rows, TODAY, get=lambda url: gh)["ads"][0]
    assert ad["keep"] and ad["posted"] == "2026-11-11"


def test_pages_option_works_after_the_command(capsys, tmp_path):
    assert main(["ledger", "--pages", "data/pages_2026-11-23.json"]) == 0
    assert main(["--pages", "data/pages_2026-11-23.json", "ledger"]) == 0
    assert capsys.readouterr().out.count("closes") == 2


def test_another_read_without_its_drafts_is_a_clean_error(capsys, tmp_path):
    data = json.loads(open("data/pages_2026-11-23.json").read())
    data["read_on"] = "2026-11-30"
    p = tmp_path / "pages_2026-11-30.json"
    p.write_text(json.dumps(data))
    assert main(["drafts", "utilitra", "--first-name", "Sam", "--pages", str(p)]) == 2
    assert "drafts_2026-11-30.json" in capsys.readouterr().err


def test_payload_command_with_first_name(capsys):
    assert main(["payload", "utilitra", "--profile-url", "https://www.linkedin.com/in/example-person", "--first-name", "Dana"]) == 0
    body = json.loads(capsys.readouterr().out)
    assert body["accountLeadPairs"][0]["lead"]["firstName"] == "Dana"
