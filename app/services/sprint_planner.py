"""Deterministic sprint planning: fit an ordered backlog into sprints before a deadline."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, timedelta
from statistics import median

PRIORITY_ORDER = {"highest": 0, "blocker": 0, "critical": 0, "high": 1, "major": 1, "medium": 2,
                  "low": 3, "minor": 3, "lowest": 4, "trivial": 4}


@dataclass
class Sprint:
    index: int
    start: date
    end: date
    capacity: float
    items: list[dict] = field(default_factory=list)

    @property
    def load(self) -> float:
        return sum(i["_size"] for i in self.items)


def _order(issues: list[dict]) -> list[dict]:
    """Priority first, then original (rank) order; blockers are pulled ahead of what they block."""
    pos = {i["key"]: n for n, i in enumerate(issues)}
    keyed = sorted(issues, key=lambda i: (PRIORITY_ORDER.get((i.get("priority") or "").lower(), 2), pos[i["key"]]))
    by_key = {i["key"]: i for i in issues}
    out, seen, visiting = [], set(), set()

    def visit(issue):
        k = issue["key"]
        if k in seen or k in visiting:
            return
        visiting.add(k)
        for b in issue.get("blocked_by") or []:
            if b in by_key:
                visit(by_key[b])
        visiting.discard(k)
        seen.add(k)
        out.append(issue)

    for i in keyed:
        visit(i)
    return out


def plan(
    issues: list[dict],
    *,
    deadline: date,
    start_date: date,
    sprint_length_days: int = 14,
    capacity: float,
    unit: str = "points",           # points | issues
    buffer_pct: float = 15,
    assume_unestimated_points: float | None = None,
) -> dict:
    if deadline <= start_date:
        raise ValueError("Deadline must be after the start date.")
    if capacity <= 0:
        raise ValueError("Capacity per sprint must be positive.")
    effective = round(capacity * (1 - buffer_pct / 100), 2)

    estimated = [i["points"] for i in issues if i.get("points")]
    default_pts = assume_unestimated_points or (median(estimated) if estimated else 3)
    unestimated = [i["key"] for i in issues if not i.get("points")]
    for i in issues:
        i["_size"] = 1.0 if unit == "issues" else float(i.get("points") or default_pts)

    sprints: list[Sprint] = []
    s = start_date
    while s < deadline:
        e = min(s + timedelta(days=sprint_length_days - 1), deadline)
        frac = ((e - s).days + 1) / sprint_length_days
        sprints.append(Sprint(len(sprints) + 1, s, e, round(effective * frac, 2)))
        s = e + timedelta(days=1)

    placed: dict[str, int] = {}
    overflow: list[dict] = []
    oversized: list[str] = []
    for issue in _order(issues):
        earliest = max((placed[b] for b in issue.get("blocked_by") or [] if b in placed), default=0)
        if any(b not in placed and b in {x["key"] for x in overflow} for b in issue.get("blocked_by") or []):
            overflow.append(issue)
            continue
        target = None
        for sp in sprints[earliest:]:
            if sp.load + issue["_size"] <= sp.capacity:
                target = sp
                break
        if target is None:
            empty = next((sp for sp in sprints[earliest:] if not sp.items), None)
            if empty and issue["_size"] > empty.capacity:
                target = empty
                oversized.append(issue["key"])
        if target is None:
            overflow.append(issue)
            continue
        target.items.append(issue)
        placed[issue["key"]] = target.index - 1

    risks: list[str] = []
    if unit == "points" and unestimated:
        risks.append(f"{len(unestimated)} issue(s) have no estimate; assumed {default_pts:g} points each "
                     f"({', '.join(unestimated[:10])}{'…' if len(unestimated) > 10 else ''}).")
    if oversized:
        risks.append(f"Larger than a whole sprint, consider splitting: {', '.join(oversized)}.")
    blocked_cross = [i["key"] for i in issues if any(b not in {x['key'] for x in issues} for b in i.get("blocked_by") or [])]
    if blocked_cross:
        risks.append(f"Blocked by issues outside this scope: {', '.join(blocked_cross[:10])}.")
    for sp in sprints:
        loads: dict[str, float] = {}
        for it in sp.items:
            loads[it.get("assignee") or "Unassigned"] = loads.get(it.get("assignee") or "Unassigned", 0) + it["_size"]
        named = {k: v for k, v in loads.items() if k != "Unassigned"}
        if len(named) >= 2:
            top, val = max(named.items(), key=lambda kv: kv[1])
            if val > 0.5 * sp.load:
                risks.append(f"Sprint {sp.index}: {top} carries {val:g} of {sp.load:g} {unit}.")
    unassigned = sum(1 for i in issues if (i.get("assignee") or "Unassigned") == "Unassigned")
    if unassigned:
        risks.append(f"{unassigned} issue(s) are unassigned.")

    overflow_size = sum(i["_size"] for i in overflow)
    extra_sprints = math.ceil(overflow_size / effective) if overflow_size else 0
    projected_end = (sprints[-1].end if sprints else start_date) + timedelta(days=extra_sprints * sprint_length_days)
    total_size = sum(i["_size"] for i in issues)
    # Raw capacity per sprint (before buffer) that would fit the whole scope in the available sprints.
    full_sprint_equivalents = sum(sp.capacity for sp in sprints) / effective
    needed_capacity = round(total_size / full_sprint_equivalents / (1 - buffer_pct / 100), 1)

    for i in issues:
        i.pop("_size", None)
    return {
        "unit": unit,
        "capacity_per_sprint": capacity,
        "effective_capacity": effective,
        "buffer_pct": buffer_pct,
        "start_date": start_date.isoformat(),
        "deadline": deadline.isoformat(),
        "sprint_length_days": sprint_length_days,
        "total_scope": round(total_size, 1),
        "fits": not overflow,
        "sprints": [{
            "sprint": f"Sprint {sp.index}",
            "start": sp.start.isoformat(),
            "end": sp.end.isoformat(),
            "capacity": sp.capacity,
            "planned": round(sum((1 if unit == "issues" else (it.get("points") or default_pts)) for it in sp.items), 1),
            "issues": [{"key": it["key"], "summary": it["summary"], "points": it.get("points"),
                        "priority": it.get("priority"), "assignee": it.get("assignee"), "status": it.get("status")}
                       for it in sp.items],
        } for sp in sprints],
        "overflow": [{"key": i["key"], "summary": i["summary"], "points": i.get("points"), "priority": i.get("priority")}
                     for i in overflow],
        "overflow_size": round(overflow_size, 1),
        "extra_sprints_needed": extra_sprints,
        "projected_completion": projected_end.isoformat(),
        "capacity_needed_per_sprint": needed_capacity,
        "risks": risks,
    }


def plan_rows(p: dict) -> tuple[list[str], list[list]]:
    cols = ["Sprint", "Start", "End", "Key", "Summary", "Points", "Priority", "Assignee", "Status"]
    rows = []
    for sp in p["sprints"]:
        for it in sp["issues"]:
            rows.append([sp["sprint"], sp["start"], sp["end"], it["key"], it["summary"], it["points"],
                         it["priority"], it["assignee"], it["status"]])
    for it in p["overflow"]:
        rows.append(["Overflow (after deadline)", "", "", it["key"], it["summary"], it["points"], it["priority"], "", ""])
    return cols, rows
