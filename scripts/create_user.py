"""Create or update a user.

Usage: python scripts/create_user.py USERNAME PASSWORD [--admin] [--agents hr,finance,pm] [--name "Full Name"]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from app.agents.registry import AGENTS  # noqa: E402
from app.auth.security import hash_password  # noqa: E402
from app.db.models import User  # noqa: E402
from app.db.session import init_db, session_scope  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("username")
    ap.add_argument("password")
    ap.add_argument("--admin", action="store_true")
    ap.add_argument("--agents", default="", help=f"comma list from: {','.join(AGENTS)}")
    ap.add_argument("--name", default="")
    a = ap.parse_args()
    agents = [x.strip() for x in a.agents.split(",") if x.strip()] or (list(AGENTS) if a.admin else [])
    bad = [x for x in agents if x not in AGENTS]
    if bad:
        sys.exit(f"Unknown agents: {bad}")
    init_db()
    with session_scope() as s:
        u = s.scalar(select(User).where(User.username == a.username.lower())) or User(username=a.username.lower())
        u.password_hash = hash_password(a.password)
        u.role = "admin" if a.admin else "user"
        u.allowed_agents = agents
        u.full_name = a.name or u.full_name or a.username
        u.is_active = True
        s.add(u)
    print(f"Saved {a.username} ({'admin' if a.admin else 'user'}) agents={agents}")


if __name__ == "__main__":
    main()
