"""HTTP 接口测试：认证、拒答、会话 CRUD 与流式响应。"""
import asyncio
from datetime import timedelta

import main as main_module
from app.core.database import get_db
from app.core.hashing import get_password_hash
from app.core.security import create_access_token
from app.models.user import User
from app.services.indexing_service import IndexingService
from app.services.llm_factory import LLMFactory

EMAIL = "tester@example.com"
OTHER_EMAIL = "other@example.com"
PASSWORD = "secret123"


def token_for(email):
    return {"Authorization": f"Bearer {create_access_token({'sub': email}, timedelta(minutes=30))}"}


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_register_login_and_duplicate_rejection(client):
    created = client.post("/api/register", json={
        "username": "newuser", "email": "new@example.com", "password": "pw123456"
    })
    assert created.status_code == 200
    assert created.json()["email"] == "new@example.com"

    duplicate = client.post("/api/register", json={
        "username": "newuser", "email": "new@example.com", "password": "pw123456"
    })
    assert duplicate.status_code == 400

    logged = client.post("/api/token", json={"email": "new@example.com", "password": "pw123456"})
    assert logged.status_code == 200
    assert logged.json()["token_type"] == "bearer"

    wrong = client.post("/api/token", json={"email": "new@example.com", "password": "bad"})
    assert wrong.status_code == 401


def test_unauthenticated_requests_are_rejected(client):
    """拒答规则：所有业务接口在没有 Bearer Token 时必须返回 401。"""
    cases = [
        ("get", "/api/users/me", None),
        ("post", "/api/chat", {"messages": [], "user_id": 1, "conversation_id": 1}),
        ("post", "/api/reason", {"messages": [], "user_id": 1}),
        ("post", "/api/search", {"messages": [], "user_id": 1, "conversation_id": 1}),
        ("post", "/api/langgraph/query", {"query": "hi", "user_id": 1}),
        ("post", "/api/conversations", None),
        ("get", "/api/conversations/user/1", None),
        ("post", "/api/langgraph/resume", {"query": "hi", "user_id": 1, "conversation_id": "x"}),
    ]
    for method, path, payload in cases:
        response = getattr(client, method)(path, json=payload) if payload else getattr(client, method)(path)
        assert response.status_code == 401, path


def test_upload_image_requires_auth(client):
    response = client.post(
        "/api/upload/image", files={"image": ("a.png", b"binary", "image/png")}
    )
    assert response.status_code == 401


def test_invalid_token_is_rejected(client):
    response = client.get("/api/users/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert response.status_code == 401


def test_current_user_endpoint(client, auth_headers):
    response = client.get("/api/users/me", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["email"] == EMAIL


def test_conversation_crud_and_ownership_rejection(client, db, auth_headers):
    engine, session_factory = db

    async def add_other_user():
        async with session_factory() as session:
            session.add(User(
                username="other", email=OTHER_EMAIL,
                password_hash=get_password_hash(PASSWORD),
            ))
            await session.commit()

    asyncio.run(add_other_user())

    created = client.post("/api/conversations", headers=auth_headers)
    assert created.status_code == 200
    conversation_id = created.json()["conversation_id"]

    listed = client.get("/api/conversations/user/1", headers=auth_headers)
    assert listed.status_code == 200

    renamed = client.put(
        f"/api/conversations/{conversation_id}/name",
        json={"name": "退货咨询"}, headers=auth_headers,
    )
    assert renamed.status_code == 200

    messages = client.get(
        f"/api/conversations/{conversation_id}/messages?user_id=1", headers=auth_headers
    )
    assert messages.status_code == 200
    assert messages.json() == []

    deleted = client.delete(f"/api/conversations/{conversation_id}", headers=auth_headers)
    assert deleted.status_code == 200

    # 跨用户访问必须被拒绝
    assert client.get("/api/conversations/user/1", headers=token_for(OTHER_EMAIL)).status_code == 403
    assert client.get(
        f"/api/conversations/{conversation_id}/messages?user_id=1",
        headers=token_for(OTHER_EMAIL),
    ).status_code == 403


def test_chat_stream_uses_token_user(client, auth_headers, monkeypatch):
    seen = {}

    class StubChatService:
        async def generate_stream(self, messages, user_id, conversation_id, on_complete=None):
            seen["user_id"] = user_id
            yield 'data: "你好"\n\n'

    monkeypatch.setattr(LLMFactory, "create_chat_service", staticmethod(lambda: StubChatService()))
    response = client.post("/api/chat", json={
        "messages": [{"role": "user", "content": "hi"}],
        "user_id": 999,
        "conversation_id": 1,
    }, headers=auth_headers)

    assert response.status_code == 200
    assert "你好" in response.text
    assert seen["user_id"] == 1  # 请求体里的 user_id 不生效


def test_reason_stream(client, auth_headers, monkeypatch):
    class StubReasonService:
        async def generate_stream(self, messages):
            yield 'data: "思考完成"\n\n'

    monkeypatch.setattr(LLMFactory, "create_reasoner_service", staticmethod(lambda: StubReasonService()))
    response = client.post("/api/reason", json={
        "messages": [{"role": "user", "content": "1+1?"}], "user_id": 1
    }, headers=auth_headers)
    assert response.status_code == 200
    assert "思考完成" in response.text


def test_upload_sanitizes_filename(client, auth_headers, monkeypatch, tmp_path):
    monkeypatch.setattr(main_module, "UPLOAD_DIR", tmp_path)

    class StubIndexing:
        async def process_file(self, file_info):
            return {"status": "success"}

    monkeypatch.setattr(IndexingService, "process_file", StubIndexing.process_file)

    response = client.post(
        "/api/upload",
        files={"file": ("../../evil.txt", b"content", "text/plain")},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["original_name"] == "evil.txt"
    assert not any(part == ".." for part in response.json()["path"].split("/"))


def test_spa_deep_link_falls_back_to_index(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert "<html" in response.text.lower()
