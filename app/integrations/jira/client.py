"""Read-only async Jira Cloud client (REST v3 + Agile 1.0).

Only GET requests plus POST /rest/api/3/search/jql (a read endpoint) are implemented, by design.
"""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any

import httpx

from app.integrations.jira.store import JiraCreds, get_credentials

CACHE_TTL = 300
_cache: dict[tuple, tuple[float, Any]] = {}
_fields_cache: dict[str, dict] = {}

PRIORITY_ORDER = {"highest": 0, "blocker": 0, "critical": 0, "high": 1, "major": 1, "medium": 2,
                  "low": 3, "minor": 3, "lowest": 4, "trivial": 4}


class JiraError(Exception):
    pass


class JiraClient:
    def __init__(self, creds: JiraCreds, user_id: int, transport: httpx.AsyncBaseTransport | None = None):
        self.creds = creds
        self.user_id = user_id
        self._transport = transport

    @classmethod
    async def for_user(cls, user_id: int) -> "JiraClient":
        return cls(await get_credentials(user_id), user_id)

    async def _request(self, method: str, path: str, *, params: dict | None = None, body: dict | None = None) -> Any:
        if method not in ("GET", "POST") or (method == "POST" and path != "/rest/api/3/search/jql"):
            raise JiraError("This client is read-only.")
        key = (self.user_id, self.creds.base_url, method, path, json.dumps(params, sort_keys=True, default=str),
               json.dumps(body, sort_keys=True, default=str))
        hit = _cache.get(key)
        if hit and hit[0] > time.time():
            return hit[1]
        headers = {**self.creds.headers, "Accept": "application/json"}
        async with httpx.AsyncClient(base_url=self.creds.base_url, timeout=30, transport=self._transport) as http:
            for attempt in range(4):
                r = await http.request(method, path, params=params, json=body, headers=headers)
                if r.status_code == 429 or r.status_code >= 500:
                    delay = float(r.headers.get("Retry-After", 2 ** attempt))
                    await asyncio.sleep(min(delay, 10))
                    continue
                break
        if r.status_code == 401:
            raise JiraError("Jira rejected the credentials (401). Please reconnect Jira.")
        if r.status_code == 403:
            raise JiraError("You don't have permission to see this in Jira (403).")
        if r.status_code == 404:
            raise JiraError(f"Not found in Jira: {path}")
        if r.status_code >= 400:
            try:
                detail = "; ".join(r.json().get("errorMessages", [])) or r.text[:300]
            except ValueError:
                detail = r.text[:300]
            raise JiraError(f"Jira error {r.status_code}: {detail}")
        data = r.json()
        _cache[key] = (time.time() + CACHE_TTL, data)
        return data

    async def get(self, path: str, **params) -> Any:
        return await self._request("GET", path, params={k: v for k, v in params.items() if v is not None})

    # ---------- fields ----------
    async def fields(self) -> dict:
        """Map of logical field -> list of field ids on this site (story points differ per project type)."""
        if self.creds.base_url in _fields_cache:
            return _fields_cache[self.creds.base_url]
        all_fields = await self.get("/rest/api/3/field")
        by_name: dict[str, list[str]] = {"story_points": [], "sprint": [], "epic_link": [], "start_date": []}
        for f in all_fields:
            name = f.get("name", "").lower()
            if name in ("story points", "story point estimate"):
                by_name["story_points"].append(f["id"])
            elif name == "sprint":
                by_name["sprint"].append(f["id"])
            elif name == "epic link":
                by_name["epic_link"].append(f["id"])
            elif name == "start date":
                by_name["start_date"].append(f["id"])
        _fields_cache[self.creds.base_url] = by_name
        return by_name

    # ---------- searches ----------
    async def search(self, jql: str, max_results: int = 100) -> list[dict]:
        f = await self.fields()
        wanted = ["summary", "status", "priority", "assignee", "issuetype", "duedate", "parent", "issuelinks",
                  "labels", "created", "updated", "resolutiondate", *f["story_points"], *f["sprint"],
                  *f["epic_link"], *f["start_date"]]
        issues: list[dict] = []
        token = None
        while len(issues) < max_results:
            body = {"jql": jql, "fields": wanted, "maxResults": min(100, max_results - len(issues))}
            if token:
                body["nextPageToken"] = token
            data = await self._request("POST", "/rest/api/3/search/jql", body=body)
            issues += [self._normalise(i, f) for i in data.get("issues", [])]
            token = data.get("nextPageToken")
            if not token or data.get("isLast", True):
                break
        return issues

    def _normalise(self, raw: dict, f: dict) -> dict:
        fl = raw.get("fields", {})
        points = next((fl.get(fid) for fid in f["story_points"] if fl.get(fid) is not None), None)
        sprints = next((fl.get(fid) for fid in f["sprint"] if fl.get(fid)), None) or []
        blocked_by, blocks = [], []
        for link in fl.get("issuelinks") or []:
            t = link.get("type", {})
            if "inwardIssue" in link and t.get("inward", "").lower() in ("is blocked by", "depends on"):
                blocked_by.append(link["inwardIssue"]["key"])
            if "outwardIssue" in link and t.get("outward", "").lower() in ("blocks",):
                blocks.append(link["outwardIssue"]["key"])
            if "outwardIssue" in link and t.get("outward", "").lower() in ("is blocked by", "depends on"):
                blocked_by.append(link["outwardIssue"]["key"])
        parent = fl.get("parent") or {}
        epic = next((fl.get(fid) for fid in f["epic_link"] if fl.get(fid)), None) or parent.get("key")
        status = fl.get("status") or {}
        return {
            "key": raw["key"],
            "summary": fl.get("summary", ""),
            "type": (fl.get("issuetype") or {}).get("name", ""),
            "status": status.get("name", ""),
            "status_category": (status.get("statusCategory") or {}).get("name", ""),
            "priority": (fl.get("priority") or {}).get("name", ""),
            "assignee": (fl.get("assignee") or {}).get("displayName", "Unassigned"),
            "points": points,
            "epic": epic,
            "sprint": sprints[-1].get("name") if sprints and isinstance(sprints[-1], dict) else None,
            "due": fl.get("duedate"),
            "blocked_by": blocked_by,
            "blocks": blocks,
            "labels": fl.get("labels") or [],
            "resolved": fl.get("resolutiondate"),
            "url": f"{self.creds.site_url}/browse/{raw['key']}",
        }

    # ---------- projects / boards / sprints ----------
    async def projects(self, query: str = "") -> list[dict]:
        out, start = [], 0
        while True:
            data = await self.get("/rest/api/3/project/search", query=query or None, startAt=start, maxResults=50)
            out += [{"key": p["key"], "name": p["name"], "type": p.get("projectTypeKey"),
                     "style": "team-managed" if p.get("style") == "next-gen" else "company-managed"}
                    for p in data.get("values", [])]
            if data.get("isLast", True):
                return out
            start += 50

    async def boards(self, project_key: str | None = None) -> list[dict]:
        data = await self.get("/rest/agile/1.0/board", projectKeyOrId=project_key, maxResults=50)
        return [{"id": b["id"], "name": b["name"], "type": b["type"],
                 "project": (b.get("location") or {}).get("projectKey")} for b in data.get("values", [])]

    async def sprints(self, board_id: int, state: str = "active,future") -> list[dict]:
        out, start = [], 0
        while True:
            data = await self.get(f"/rest/agile/1.0/board/{board_id}/sprint", state=state, startAt=start, maxResults=50)
            out += [{"id": s["id"], "name": s["name"], "state": s["state"], "start": s.get("startDate"),
                     "end": s.get("endDate"), "complete": s.get("completeDate"), "goal": s.get("goal", "")}
                    for s in data.get("values", [])]
            if data.get("isLast", True):
                return out
            start += 50

    async def velocity(self, board_id: int, last_n: int = 5) -> dict:
        closed = (await self.sprints(board_id, "closed"))[-last_n:]
        rows = []
        for sp in closed:
            done = await self.search(f"sprint = {sp['id']} AND statusCategory = Done", max_results=300)
            rows.append({"sprint": sp["name"], "completed_points": sum(i["points"] or 0 for i in done),
                         "completed_issues": len(done), "end": (sp.get("complete") or sp.get("end") or "")[:10]})
        pts = [r["completed_points"] for r in rows]
        return {"sprints": rows, "average_points": round(sum(pts) / len(pts), 1) if pts else None,
                "average_issues": round(sum(r["completed_issues"] for r in rows) / len(rows), 1) if rows else None}

    async def issue(self, key: str) -> dict:
        f = await self.fields()
        raw = await self.get(f"/rest/api/3/issue/{key}")
        item = self._normalise(raw, f)
        desc = raw.get("fields", {}).get("description")
        item["description"] = _adf_text(desc)[:3000] if desc else ""
        return item

    async def assignable_users(self, project_key: str) -> list[dict]:
        data = await self.get("/rest/api/3/user/assignable/search", project=project_key, maxResults=100)
        return [{"name": u.get("displayName"), "active": u.get("active")} for u in data if u.get("accountType") == "atlassian"]


def _adf_text(node: Any) -> str:
    """Flatten Atlassian Document Format to plain text."""
    if isinstance(node, dict):
        if node.get("type") == "text":
            return node.get("text", "")
        sep = "\n" if node.get("type") in ("paragraph", "heading", "listItem") else ""
        return "".join(_adf_text(c) for c in node.get("content", [])) + sep
    if isinstance(node, list):
        return "".join(_adf_text(c) for c in node)
    return str(node or "")
