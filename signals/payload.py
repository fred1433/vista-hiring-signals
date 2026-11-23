"""Hand-off to the sender. HeyReach adds people, not companies: the person is chosen in Sales Navigator first.
Shape from the HeyReach public API collection (AddLeadsToCampaignV2, read 23 Nov 2026): up to 100 leads per
request, customUserFields names limited to letters, digits and underscores, 300 requests per minute."""
from __future__ import annotations

import re

STATUS_LABEL = {"matched": "matched", "hold": "on hold", "excluded": "excluded"}
PROFILE = re.compile(r"^https://(www\.)?linkedin\.com/(in|sales/lead)/[^\s/?#]+/?$")
FIELD_NAME = re.compile(r"^[A-Za-z0-9_]+$")


class PayloadError(ValueError):
    pass


def custom_fields(acc: dict) -> list[dict]:
    lead = next(p for p in acc["pages"] if p["id"] == acc["lead_page"])
    vista = next((p for p in acc["pages"] if p["code"] in ("names_vista", "migrating_to_vista")), lead)
    vq = next((q for q in vista["quotes"] if "vista" in q.lower()), vista["title"])
    fields = [
        {"name": "company_signal", "value": f"{lead['title']} ad, posted {lead['posted']}"},
        {"name": "signal_quote", "value": next((q for q in lead["quotes"] if "statement" in q.lower()), vq)},
        {"name": "erp_quote", "value": vq},
        {"name": "ad_date", "value": lead["posted"] or ""},
        {"name": "ad_url", "value": lead["url"]},
    ]
    for f in fields:
        if not FIELD_NAME.match(f["name"]):
            raise PayloadError(f"HeyReach rejects field name {f['name']!r}")
    return fields


MESSAGE_FIELDS = {"note": "connection_note", "followup_1": "followup_1", "followup_2": "followup_2"}


def heyreach(acc: dict, profile_url: str | None, campaign_id: int | None = None, sender_id: int | None = None,
             first_name: str | None = None, messages: dict | None = None) -> dict:
    """messages: the drafts already rendered and validated for first_name (signals.drafts.render)."""
    if acc.get("status") != "matched":
        raise PayloadError(f"{acc['employer']} is {STATUS_LABEL.get(acc.get('status'), acc.get('status'))}: only matched accounts are handed to the sender")
    if not profile_url:
        raise PayloadError("pass --profile-url: the LinkedIn profile of the person you chose in Sales Navigator")
    if not PROFILE.match(profile_url):
        raise PayloadError(f"not a LinkedIn profile URL: {profile_url}")
    return {
        "campaignId": campaign_id if campaign_id is not None else "YOUR_CAMPAIGN_ID",
        "accountLeadPairs": [{
            "linkedInAccountId": sender_id if sender_id is not None else "YOUR_SENDER_ID",
            "lead": _lead(acc, profile_url, first_name, messages),
        }],
        "resumeFinishedCampaign": False,
        "resumePausedCampaign": False,
    }


def _lead(acc: dict, profile_url: str, first_name: str | None, messages: dict | None) -> dict:
    lead = {}
    if first_name and first_name.strip():
        lead["firstName"] = first_name.strip()
    lead.update(profileUrl=profile_url, companyName=acc["employer"], customUserFields=custom_fields(acc))
    for k, name in MESSAGE_FIELDS.items():
        if messages and k in messages:
            lead["customUserFields"].append({"name": name, "value": messages[k]})
    return lead
