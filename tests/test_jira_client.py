import asyncio
import json

import httpx
import pytest

from app.integrations.jira import client as jc
from app.integrations.jira.client import JiraClient, JiraError
from app.integrations.jira.store import JiraCreds

FIELDS = [{"id": "customfield_10016", "name": "Story point estimate"}, {"id": "customfield_10020", "name": "Sprint"}]


def make_client(handler):
    jc._cache.clear()
    jc._fields_cache.clear()
    return JiraClient(JiraCreds("https://x.atlassian.net", "https://x.atlassian.net", {"Authorization": "Basic t"}), 1,
                      transport=httpx.MockTransport(handler))


def test_search_paginates_and_normalises():
    calls = []

    def handler(req: httpx.Request):
        if req.url.path == "/rest/api/3/field":
            return httpx.Response(200, json=FIELDS)
        body = json.loads(req.content)
        calls.append(body)
        if "nextPageToken" not in body:
            return httpx.Response(200, json={"issues": [{"key": "A-1", "fields": {"summary": "one", "customfield_10016": 3,
                                                         "status": {"name": "To Do", "statusCategory": {"name": "To Do"}},
                                                         "issuelinks": [{"type": {"inward": "is blocked by"},
                                                                         "inwardIssue": {"key": "A-2"}}]}}],
                                             "nextPageToken": "p2", "isLast": False})
        return httpx.Response(200, json={"issues": [{"key": "A-2", "fields": {"summary": "two"}}], "isLast": True})

    issues = asyncio.run(make_client(handler).search("project = A"))
    assert [i["key"] for i in issues] == ["A-1", "A-2"]
    assert issues[0]["points"] == 3 and issues[0]["blocked_by"] == ["A-2"]
    assert len(calls) == 2


def test_retries_on_429(monkeypatch):
    real_sleep = asyncio.sleep
    monkeypatch.setattr(jc.asyncio, "sleep", lambda s: real_sleep(0))
    state = {"n": 0}

    def handler(req):
        state["n"] += 1
        if state["n"] == 1:
            return httpx.Response(429, headers={"Retry-After": "1"})
        return httpx.Response(200, json={"values": [], "isLast": True})

    assert asyncio.run(make_client(handler).projects()) == []
    assert state["n"] == 2


def test_auth_error_and_read_only():
    c = make_client(lambda req: httpx.Response(401, json={}))
    with pytest.raises(JiraError, match="401"):
        asyncio.run(c.projects())
    with pytest.raises(JiraError, match="read-only"):
        asyncio.run(c._request("POST", "/rest/api/3/issue", body={}))
