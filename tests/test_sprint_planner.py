from datetime import date

import pytest

from app.services.sprint_planner import plan


def issue(key, points=None, priority="Medium", assignee="Ann", blocked_by=None):
    return {"key": key, "summary": key, "points": points, "priority": priority, "assignee": assignee,
            "blocked_by": blocked_by or [], "status": "To Do"}


def test_fits_and_respects_priority():
    issues = [issue("A", 5, "Low"), issue("B", 5, "Highest"), issue("C", 5)]
    p = plan(issues, deadline=date(2026, 11, 1), start_date=date(2026, 10, 1), sprint_length_days=14,
             capacity=10, buffer_pct=0)
    assert p["fits"]
    assert [i["key"] for i in p["sprints"][0]["issues"]] == ["B", "C"]


def test_blockers_scheduled_first_and_overflow():
    issues = [issue("X", 8, "Highest", blocked_by=["Y"]), issue("Y", 8, "Low"), issue("Z", 8)]
    p = plan(issues, deadline=date(2026, 10, 28), start_date=date(2026, 10, 1), sprint_length_days=14,
             capacity=10, buffer_pct=0)
    order = [i["key"] for sp in p["sprints"] for i in sp["issues"]]
    assert order.index("Y") < order.index("X")
    assert not p["fits"] and p["overflow"] and p["extra_sprints_needed"] >= 1


def test_issue_count_mode_and_risks():
    issues = [issue(f"I{n}", assignee="Bob" if n < 8 else "Cat") for n in range(10)]
    p = plan(issues, deadline=date(2026, 10, 15), start_date=date(2026, 10, 1), sprint_length_days=14,
             capacity=12, unit="issues", buffer_pct=0)
    assert p["fits"] and p["sprints"][0]["planned"] == 10
    assert any("Bob carries" in r for r in p["risks"])


def test_unestimated_assumption_reported():
    p = plan([issue("A", 3), issue("B")], deadline=date(2026, 10, 30), start_date=date(2026, 10, 1), capacity=10)
    assert any("no estimate" in r for r in p["risks"])


def test_invalid_inputs():
    with pytest.raises(ValueError):
        plan([], deadline=date(2026, 1, 1), start_date=date(2026, 2, 1), capacity=5)
