import pytest

from signals import watch
from signals.__main__ import main


def test_ledger_command(capsys):
    assert main(["ledger"]) == 0
    assert "closes" in capsys.readouterr().out


def test_drafts_without_first_name_shows_templates(capsys):
    assert main(["drafts", "utilitra"]) == 0
    assert "Note budget" in capsys.readouterr().out


def test_drafts_for_held_account_is_a_clean_error(capsys):
    assert main(["drafts", "mastec", "--first-name", "Sam"]) == 2


def test_unknown_account_is_a_clean_error(capsys):
    assert main(["drafts", "nobody"]) == 2
    assert "Known accounts" in capsys.readouterr().err


def test_payload_without_profile_is_a_clean_error(capsys):
    assert main(["payload", "utilitra"]) == 2
    assert "--profile-url" in capsys.readouterr().err


def test_check_command_relative_date(capsys):
    assert main(["check", "Experience with Viewpoint Vista essential", "--title", "AP Officer", "--posted", "5mo ago"]) == 0
    assert "expired" in capsys.readouterr().out


@pytest.mark.parametrize("url", ["https://www.indeed.com/jobs?q=vista", "https://au.jora.com/j?q=vista",
                                 "https://www.seek.com.au/jobs", "https://www.linkedin.com/jobs/view/1",
                                 "https://www.simplyhired.com/search?q=vista", "https://www.ziprecruiter.com/jobs"])
def test_job_boards_are_refused(url):
    with pytest.raises(watch.Blocked):
        watch.guard(url)


def test_watch_plan_only_reads_employer_feeds():
    for p in watch.plan():
        watch.guard(p["url"])


def test_mcp_tools_registered():
    mcp_mod = pytest.importorskip("mcp")
    import asyncio
    from signals.mcp_server import mcp
    names = {t.name for t in asyncio.run(mcp.list_tools())}
    assert names == {"check_ad", "apply_rules", "draft_messages", "build_payload"}
