"""Per-user Jira connections (encrypted at rest) and credential resolution with OAuth refresh."""
from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime, timedelta

import httpx

from app.auth.security import decrypt_json, encrypt_json
from app.config import get_settings
from app.db.models import JiraConnection, utcnow
from app.db.session import session_scope

TOKEN_URL = "https://auth.atlassian.com/oauth/token"


class JiraNotConnected(Exception):
    pass


@dataclass
class JiraCreds:
    base_url: str      # where REST calls go
    site_url: str      # human-facing site, for links
    headers: dict


def save_connection(user_id: int, *, auth_type: str, site_url: str, secret: dict, cloud_id: str | None = None,
                    account_email: str = "", account_name: str = "", expires_at: datetime | None = None,
                    scopes: str = "") -> None:
    with session_scope() as s:
        conn = s.get(JiraConnection, user_id) or JiraConnection(user_id=user_id)
        conn.auth_type = auth_type
        conn.site_url = site_url.rstrip("/")
        conn.cloud_id = cloud_id
        conn.account_email = account_email
        conn.account_name = account_name
        conn.secret_enc = encrypt_json(secret)
        conn.expires_at = expires_at
        conn.scopes = scopes
        conn.connected_at = utcnow()
        s.merge(conn)


def delete_connection(user_id: int) -> bool:
    with session_scope() as s:
        conn = s.get(JiraConnection, user_id)
        if conn:
            s.delete(conn)
            return True
    return False


def get_connection(user_id: int) -> JiraConnection | None:
    with session_scope() as s:
        return s.get(JiraConnection, user_id)


def describe_connection(user_id: int) -> str:
    conn = get_connection(user_id)
    if conn is None:
        return "NOT CONNECTED. Ask the user to click 'Connect Jira' in the PM panel of the app."
    return f"connected to {conn.site_url} as {conn.account_name or conn.account_email} ({conn.auth_type})."


async def _refresh_oauth(user_id: int, conn: JiraConnection, secret: dict) -> dict:
    s = get_settings()
    async with httpx.AsyncClient(timeout=30) as http:
        r = await http.post(TOKEN_URL, json={
            "grant_type": "refresh_token",
            "client_id": s.jira_oauth_client_id,
            "client_secret": s.jira_oauth_client_secret,
            "refresh_token": secret["refresh_token"],
        })
    if r.status_code != 200:
        raise JiraNotConnected("Jira authorization expired; please reconnect Jira.")
    tok = r.json()
    secret = {"access_token": tok["access_token"], "refresh_token": tok.get("refresh_token", secret["refresh_token"])}
    save_connection(user_id, auth_type="oauth", site_url=conn.site_url, secret=secret, cloud_id=conn.cloud_id,
                    account_email=conn.account_email, account_name=conn.account_name,
                    expires_at=utcnow() + timedelta(seconds=int(tok.get("expires_in", 3600)) - 60), scopes=conn.scopes)
    return secret


async def get_credentials(user_id: int) -> JiraCreds:
    conn = get_connection(user_id)
    if conn is None:
        raise JiraNotConnected("Jira is not connected for this user.")
    secret = decrypt_json(conn.secret_enc)
    if conn.auth_type == "oauth":
        if conn.expires_at and conn.expires_at <= utcnow():
            secret = await _refresh_oauth(user_id, conn, secret)
        return JiraCreds(f"https://api.atlassian.com/ex/jira/{conn.cloud_id}", conn.site_url,
                         {"Authorization": f"Bearer {secret['access_token']}"})
    if conn.auth_type == "pat":  # Jira Server / Data Center
        return JiraCreds(conn.site_url, conn.site_url, {"Authorization": f"Bearer {secret['token']}"})
    basic = base64.b64encode(f"{conn.account_email}:{secret['api_token']}".encode()).decode()
    return JiraCreds(conn.site_url, conn.site_url, {"Authorization": f"Basic {basic}"})


async def verify_api_token(site_url: str, email: str, api_token: str) -> dict:
    """Validate credentials with a read-only call; returns /myself payload."""
    site_url = site_url.rstrip("/")
    if not site_url.startswith("https://"):
        site_url = "https://" + site_url.removeprefix("http://")
    async with httpx.AsyncClient(timeout=20) as http:
        r = await http.get(f"{site_url}/rest/api/3/myself", auth=(email, api_token), headers={"Accept": "application/json"})
    if r.status_code != 200:
        raise ValueError(f"Jira rejected the credentials (HTTP {r.status_code}).")
    return {"site_url": site_url, **r.json()}
