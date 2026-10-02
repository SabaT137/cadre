import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.services import usage


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _login(client, username, password):
    r = client.post("/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_requires_auth(client):
    assert client.post("/chat", json={"message": "hi"}).status_code == 401
    assert client.get("/templates").status_code == 401


def test_bad_password(client):
    assert client.post("/auth/login", json={"username": "admin", "password": "wrong"}).status_code == 401


def test_admin_can_create_user_and_user_is_restricted(client):
    admin = _login(client, "admin", "admin-pass")
    r = client.post("/admin/users", headers=admin, json={"username": "fin_t", "password": "pw1234", "allowed_agents": ["finance"]})
    assert r.status_code == 201, r.text
    user = _login(client, "fin_t", "pw1234")
    assert client.get("/admin/stats", headers=user).status_code == 403
    me = client.get("/auth/me", headers=user).json()
    assert [a["name"] for a in me["available_agents"]] == ["finance"]


def test_disabled_agent_hidden(client):
    admin = _login(client, "admin", "admin-pass")
    assert client.patch("/admin/agents/developer", headers=admin, json={"enabled": False}).status_code == 200
    names = [a["name"] for a in client.get("/auth/me", headers=admin).json()["available_agents"]]
    assert "developer" not in names
    client.patch("/admin/agents/developer", headers=admin, json={"enabled": True})


def test_ui_hint_for_forbidden_agent_is_refused_without_llm(client):
    user = _login(client, "fin_t", "pw1234")
    r = client.post("/chat", headers=user, json={"message": "plan my sprints", "department": "pm"})
    assert r.status_code == 200
    assert r.json()["agent"] == "supervisor" and "access" in r.json()["reply"].lower()


def test_threads_are_private(client):
    admin = _login(client, "admin", "admin-pass")
    user = _login(client, "fin_t", "pw1234")
    r = client.post("/chat", headers=user, json={"message": "invoice please", "department": "pm", "thread_id": "priv1"})
    assert r.status_code == 200
    assert client.get("/threads/priv1", headers=admin).status_code == 404
    assert client.post("/chat", headers=admin, json={"message": "x", "department": "hr", "thread_id": "priv1"}).status_code == 404
    assert any(t["thread_id"] == "priv1" for t in client.get("/threads", headers=user).json())


def test_runs_are_recorded(client):
    runs = usage.recent_runs(user="fin_t")
    assert runs and runs[0]["status"] == "refused"
    admin = _login(client, "admin", "admin-pass")
    assert client.get("/admin/stats", headers=admin).json()["refused"] >= 1


def test_file_access_is_owner_only(client):
    from app.services import usage as u
    from app.services.template_store import get_store

    admin = _login(client, "admin", "admin-pass")
    me_admin = client.get("/auth/me", headers=admin).json()
    fid, path = get_store().new_output_path("acl_test")
    path.write_bytes(b"PK test")
    u.record_documents(me_admin["id"], "t-acl", "hr", [{"type": "file", "file_id": fid, "filename": "acl.docx"}])
    user = _login(client, "fin_t", "pw1234")
    assert client.get(f"/files/{fid}", headers=user).status_code == 404
    assert client.get(f"/files/{fid}", headers=admin).status_code == 200
    docs = client.get("/documents", headers=admin).json()
    assert any(d["file_id"] == fid and d["kind"] == "contract" for d in docs)
    assert client.get("/documents", headers=user).json() == []
