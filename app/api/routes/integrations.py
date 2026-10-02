from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from app.auth.deps import CurrentUser, current_user
from app.config import get_settings
from app.integrations.jira import oauth
from app.integrations.jira import store as jira_store

router = APIRouter(prefix="/integrations/jira", tags=["integrations"])


@router.get("/status")
def status(user: CurrentUser = Depends(current_user)):
    conn = jira_store.get_connection(user.id)
    base = {"oauth_available": oauth.oauth_configured()}
    if conn is None:
        return {**base, "connected": False}
    return {**base, "connected": True, "site_url": conn.site_url, "account": conn.account_name or conn.account_email,
            "auth_type": conn.auth_type, "connected_at": conn.connected_at.isoformat(timespec="seconds")}


@router.get("/connect")
def connect(user: CurrentUser = Depends(current_user)):
    if not oauth.oauth_configured():
        raise HTTPException(400, "The Jira OAuth app is not configured yet; use an API token instead.")
    return {"authorize_url": oauth.authorize_url(user.id)}


@router.get("/callback", include_in_schema=False)
async def callback(code: str = "", state: str = "", error: str = ""):
    ui = get_settings().user_ui_url
    if error or not code:
        return RedirectResponse(f"{ui}?{urlencode({'jira': 'error', 'detail': error or 'missing code'})}")
    try:
        await oauth.complete(code, state)
    except Exception as e:
        return RedirectResponse(f"{ui}?{urlencode({'jira': 'error', 'detail': str(e)[:200]})}")
    return RedirectResponse(f"{ui}?jira=connected")


class TokenConnect(BaseModel):
    site_url: str
    email: str = ""
    api_token: str
    kind: str = "api_token"  # api_token (Cloud) | pat (Server/DC)


@router.post("/token")
async def connect_with_token(body: TokenConnect, user: CurrentUser = Depends(current_user)):
    if body.kind == "pat":
        jira_store.save_connection(user.id, auth_type="pat", site_url=body.site_url, secret={"token": body.api_token})
        return {"connected": True, "site_url": body.site_url}
    try:
        me = await jira_store.verify_api_token(body.site_url, body.email, body.api_token)
    except ValueError as e:
        raise HTTPException(400, str(e))
    jira_store.save_connection(user.id, auth_type="api_token", site_url=me["site_url"],
                               secret={"api_token": body.api_token}, account_email=body.email,
                               account_name=me.get("displayName", ""))
    return {"connected": True, "site_url": me["site_url"], "account": me.get("displayName", "")}


@router.delete("")
def disconnect(user: CurrentUser = Depends(current_user)):
    return {"disconnected": jira_store.delete_connection(user.id)}
