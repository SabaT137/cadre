"""Read-only access to the DevOps/IT database with a SQL safety guard."""
from __future__ import annotations

from functools import lru_cache

import sqlglot
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import Engine
from sqlglot import exp

from app.config import get_settings

# Human-friendly descriptions for the demo schema; tables not listed here still work via reflection.
TABLE_DESCRIPTIONS = {
    "departments": "Company departments (Engineering, DevOps, HR, ...).",
    "employees": "Staff directory: name, email, department, title, location, hire date, status.",
    "assets": "IT hardware (laptops, monitors, phones, docks): assignee, purchase date, warranty expiry, status.",
    "servers": "Servers/VMs: hostname, environment (prod/staging/dev), cloud provider, region, specs, status, owner dept, monthly cost.",
    "deployments": "Service deployments: service, target server, version, who deployed, when, outcome.",
    "incidents": "Operational incidents: severity sev1-sev4, service, server, reporter, assignee, open/resolve times, status.",
    "software_licenses": "SaaS/software licenses: seats total/used, cost per seat, renewal date.",
    "access_requests": "Requests for system access: employee, system, level, status, approver.",
}

FORBIDDEN = (
    exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create, exp.Alter, exp.Command,
    exp.Merge, exp.TruncateTable, exp.Pragma, exp.Attach, exp.Detach, exp.Transaction,
)


class UnsafeQueryError(ValueError):
    pass


@lru_cache
def get_engine() -> Engine:
    url = get_settings().resolved_db_url()
    if url.startswith("sqlite:///"):
        path = url[len("sqlite:///"):]
        engine = create_engine(
            f"sqlite:///file:{path}?mode=ro&uri=true",
            connect_args={"check_same_thread": False},
        )

        @event.listens_for(engine, "connect")
        def _ro(dbapi_conn, _):  # belt and braces on top of mode=ro
            dbapi_conn.execute("PRAGMA query_only = ON")

        return engine
    engine = create_engine(url, pool_pre_ping=True)
    if engine.dialect.name == "postgresql":
        @event.listens_for(engine, "connect")
        def _pg_ro(dbapi_conn, _):
            cur = dbapi_conn.cursor()
            cur.execute("SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY")
            cur.execute("SET statement_timeout = 15000")
            cur.close()
    return engine


def dialect_name() -> str:
    name = get_engine().dialect.name
    return {"postgresql": "postgres"}.get(name, name)


def allowed_tables() -> list[str]:
    return sorted(inspect(get_engine()).get_table_names())


def validate_sql(query: str, allowed: list[str], dialect: str = "sqlite", row_limit: int = 200) -> str:
    """Return a safe, limited version of `query` or raise UnsafeQueryError."""
    try:
        statements = [s for s in sqlglot.parse(query, read=dialect) if s is not None]
    except sqlglot.errors.ParseError as e:
        raise UnsafeQueryError(f"Could not parse SQL: {e}") from e
    if len(statements) != 1:
        raise UnsafeQueryError("Exactly one SQL statement is allowed.")
    stmt = statements[0]
    if not isinstance(stmt, (exp.Select, exp.Union, exp.Intersect, exp.Except)):
        raise UnsafeQueryError(f"Only SELECT queries are allowed (got {stmt.key.upper()}).")
    for node in stmt.walk():
        if isinstance(node, FORBIDDEN):
            raise UnsafeQueryError(f"Forbidden operation: {node.key.upper()}.")
    cte_names = {cte.alias_or_name.lower() for cte in stmt.find_all(exp.CTE)}
    allowed_lower = {t.lower() for t in allowed}
    for table in stmt.find_all(exp.Table):
        name = table.name.lower()
        if name and name not in cte_names and name not in allowed_lower:
            raise UnsafeQueryError(f"Table not allowed or does not exist: {table.name}.")
    if isinstance(stmt, exp.Select) and stmt.args.get("limit") is None:
        stmt = stmt.limit(row_limit)
    elif not isinstance(stmt, exp.Select):
        stmt = exp.select("*").from_(stmt.subquery("q")).limit(row_limit)
    return stmt.sql(dialect=dialect)


def run_query(query: str) -> tuple[str, list[str], list[list]]:
    s = get_settings()
    safe = validate_sql(query, allowed_tables(), dialect_name(), s.sql_row_limit)
    with get_engine().connect() as conn:
        result = conn.execute(text(safe))
        columns = list(result.keys())
        rows = [list(r) for r in result.fetchmany(s.sql_row_limit)]
    return safe, columns, rows


def describe_table(name: str, sample_rows: int = 3) -> str:
    insp = inspect(get_engine())
    cols = insp.get_columns(name)
    pk = set(insp.get_pk_constraint(name).get("constrained_columns") or [])
    fks = {
        c: f"{fk['referred_table']}.{fk['referred_columns'][0]}"
        for fk in insp.get_foreign_keys(name)
        for c in fk["constrained_columns"]
    }
    lines = [f"TABLE {name}: {TABLE_DESCRIPTIONS.get(name, '')}".rstrip()]
    for c in cols:
        extra = " PK" if c["name"] in pk else ""
        if c["name"] in fks:
            extra += f" -> {fks[c['name']]}"
        lines.append(f"  - {c['name']} {c['type']}{' NULL' if c.get('nullable') and not extra else ''}{extra}")
    with get_engine().connect() as conn:
        q = exp.select("*").from_(exp.to_table(name)).limit(sample_rows).sql(dialect=dialect_name())
        res = conn.execute(text(q))
        keys = list(res.keys())
        sample = res.fetchall()
    if sample:
        lines.append("  sample rows:")
        for r in sample:
            lines.append("    " + ", ".join(f"{k}={v}" for k, v in zip(keys, r)))
    return "\n".join(lines)
