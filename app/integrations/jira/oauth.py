"""Atlassian OAuth 2.0 (3LO) 'Connect Jira' flow, read-only scopes."""
from __future__ import annotations

from datetime import timedelta
from urllib.parse import urlencode

import httpx

from app.auth.security import create_token, decode_token
from app.config import get_settings
from app.db.models import utcnow
from app.integrations.jira.store import TOKEN_URL, save_connection

AUTHORIZE_URL = "https://auth.atlassian.com/authorize"
RESOURCES_URL = "https://api.atlassian.com/oauth/token/accessible-resources"
SCOPES = [
    "read:jira-work", "read:jira-user", "offline_access",
    "read:board-scope:jira-software", "read:sprint:jira-software",
    "read:project:jira", "read:issue-details:jira", "read:jql:jira",
]


def oauth_configured() -> bool:
    s = get_settings()
    return bool(s.jira_oauth_client_id and s.jira_oauth_client_secret)


def authorize_url(user_id: int) -> str:
    s = get_settings()
    state = create_token(str(user_id), purpose="jira_oauth", minutes=10)
    return AUTHORIZE_URL + "?" + urlencode({
        "audience": "api.atlassian.com",
        "client_id": s.jira_oauth_client_id,
        "scope": " ".join(SCOPES),
        "redirect_uri": s.jira_oauth_redirect_uri,
        "state": state,
        "response_type": "code",
        "prompt": "consent",
    })


async def complete(code: str, state: str) -> int:
    """Exchange the code, pick the site, store the connection. Returns the user id."""
    s = get_settings()
    user_id = int(decode_token(state, purpose="jira_oauth")["sub"])
    async with httpx.AsyncClient(timeout=30) as http:
        r = await http.post(TOKEN_URL, json={
            "grant_type": "authorization_code",
            "client_id": s.jira_oauth_client_id,
            "client_secret": s.jira_oauth_client_secret,
            "code": code,
            "redirect_uri": s.jira_oauth_redirect_uri,
        })
        r.raise_for_status()
        tok = r.json()
        headers = {"Authorization": f"Bearer {tok['access_token']}", "Accept": "application/json"}
        resources = (await http.get(RESOURCES_URL, headers=headers)).json()
        jira_sites = [x for x in resources if any("jira" in sc for sc in x.get("scopes", []))] or resources
        if not jira_sites:
            raise ValueError("No Jira site was authorised.")
        site = jira_sites[0]
        me = (await http.get(f"https://api.atlassian.com/ex/jira/{site['id']}/rest/api/3/myself", headers=headers)).json()
    save_connection(
        user_id, auth_type="oauth", site_url=site["url"], cloud_id=site["id"],
        secret={"access_token": tok["access_token"], "refresh_token": tok.get("refresh_token", "")},
        account_email=me.get("emailAddress", ""), account_name=me.get("displayName", ""),
        expires_at=utcnow() + timedelta(seconds=int(tok.get("expires_in", 3600)) - 60), scopes=tok.get("scope", ""),
    )
    return user_id
