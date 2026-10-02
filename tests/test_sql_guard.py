import pytest

from app.services.db import UnsafeQueryError, validate_sql

TABLES = ["assets", "employees", "servers"]


@pytest.mark.parametrize("query", [
    "DROP TABLE assets",
    "DELETE FROM assets",
    "UPDATE assets SET status = 'retired'",
    "INSERT INTO assets (id) VALUES (1)",
    "SELECT 1; DELETE FROM assets",
    "PRAGMA table_info(assets)",
    "ATTACH DATABASE 'x.db' AS x",
    "SELECT * FROM sqlite_master",
    "SELECT * FROM secrets",
    "CREATE TABLE t AS SELECT * FROM assets",
])
def test_rejects_unsafe(query):
    with pytest.raises(UnsafeQueryError):
        validate_sql(query, TABLES)


def test_adds_limit():
    assert validate_sql("select * from assets", TABLES).endswith("LIMIT 200")


def test_keeps_existing_limit():
    assert validate_sql("select * from assets limit 5", TABLES).endswith("LIMIT 5")


def test_allows_cte_and_joins():
    q = """with eng as (select id from employees where department_id = 1)
           select a.asset_tag from assets a join eng on a.assigned_to = eng.id"""
    assert "LIMIT 200" in validate_sql(q, TABLES)
