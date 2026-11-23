"""MCP server: the same rules, callable from Claude Code. Run: python -m signals.mcp_server (stdio)."""
from __future__ import annotations

from datetime import date

try:  # mcp 2.x
    from mcp.server.mcpserver import MCPServer as FastMCP
except ImportError:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP

from . import drafts as D
from . import ledger as L
from . import payload as P
from . import rules

mcp = FastMCP("vista-signals")


@mcp.tool()
def check_ad(title: str, text: str, employer: str = "unknown", posted: str | None = None, read_on: str | None = None) -> dict:
    """Classify one finance job ad: does it name Vista by Viewpoint, is it fresh, and why not if not."""
    ro = date.fromisoformat(read_on) if read_on else date.today()
    if posted and not posted[:4].isdigit():
        p = rules.parse_relative(posted, ro)
        posted = p.isoformat() if p else None
    page = {"id": "adhoc", "employer": employer, "title": title, "url": "", "http": 200, "posted": posted, "quotes": [text], "location": None}
    res = L.classify_page(page, ro)
    return {"code": res["code"], "freshness": res["freshness"], "vista_mentions": rules.vista_mentions(title + " " + text),
            "reason": L.page_reason(res, employer)}


@mcp.tool()
def apply_rules(pages_file: str | None = None) -> dict:
    """Build the week's ledger (matched, hold, excluded with reasons) from a pages file."""
    led = L.build(L.load(pages_file or L.DEFAULT_PAGES))
    return {"counts": led["counts"], "proof": led["proof"],
            "accounts": [{k: a[k] for k in ("id", "employer", "status", "reason", "reason_text")} for a in led["accounts"]]}


@mcp.tool()
def draft_messages(account_id: str, first_name: str) -> dict:
    """Connection note (<= 200 characters) and two follow-ups for a matched account, validated against its facts."""
    led = L.build(L.load())
    return D.render(L.account(led, account_id), led, first_name)


@mcp.tool()
def build_payload(account_id: str, profile_url: str, campaign_id: int | None = None, sender_id: int | None = None) -> dict:
    """HeyReach AddLeadsToCampaignV2 body for the person chosen in Sales Navigator. Nothing is sent."""
    led = L.build(L.load())
    return P.heyreach(L.account(led, account_id), profile_url, campaign_id, sender_id)


if __name__ == "__main__":
    mcp.run()
