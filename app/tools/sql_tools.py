from datetime import date, datetime
from decimal import Decimal

from langchain_core.tools import tool

from app.services import db


def _json_safe(v):
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, bytes):
        return v.hex()
    return v


def _markdown(columns: list[str], rows: list[list], max_rows: int = 50) -> str:
    head = "| " + " | ".join(columns) + " |\n|" + "---|" * len(columns)
    body = "\n".join("| " + " | ".join(str(c) for c in r) + " |" for r in rows[:max_rows])
    more = f"\n… {len(rows) - max_rows} more rows not shown" if len(rows) > max_rows else ""
    return f"{head}\n{body}{more}"


@tool
def list_tables() -> str:
    """List the database tables you can query, with a short description of each."""
    return "\n".join(f"- {t}: {db.TABLE_DESCRIPTIONS.get(t, '')}" for t in db.allowed_tables())


@tool
def describe_tables(tables: list[str]) -> str:
    """Show columns, types, primary/foreign keys and sample rows for the given tables. Call before writing SQL."""
    allowed = set(db.allowed_tables())
    out = []
    for t in tables:
        out.append(db.describe_table(t) if t in allowed else f"Unknown table: {t}")
    return "\n\n".join(out)


@tool(response_format="content_and_artifact")
def run_sql(query: str) -> tuple[str, dict | None]:
    """Run a single read-only SELECT query (SQLite dialect unless told otherwise) and return the rows.
    A LIMIT is added automatically. Data-modifying statements are rejected."""
    try:
        safe, columns, rows = db.run_query(query)
    except db.UnsafeQueryError as e:
        return f"REJECTED: {e}", None
    except Exception as e:  # SQL errors go back to the model so it can fix the query
        return f"SQL ERROR: {e.__class__.__name__}: {str(e).splitlines()[0][:300]}", None
    rows = [[_json_safe(v) for v in r] for r in rows]
    content = f"Executed: {safe}\nRows returned: {len(rows)}\n" + (_markdown(columns, rows) if rows else "(no rows)")
    return content, {"type": "sql", "query": safe, "columns": columns, "rows": rows}


DEVOPS_TOOLS = [list_tables, describe_tables, run_sql]
