"""测试公共夹具：每个用例使用独立的临时 SQLite 数据库，不依赖任何外部服务。"""
import asyncio
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.services import conversation_service as conversation_service_module
from app.core.database import Base, get_db
from app.core.hashing import get_password_hash
from app.core.security import create_access_token
from app.models.conversation import Conversation  # noqa: F401  注册表结构
from app.models.message import Message  # noqa: F401
from app.models.user import User
from main import app

TEST_EMAIL = "tester@example.com"
TEST_PASSWORD = "secret123"


def run(coro):
    """在同步 pytest 用例中执行协程，避免依赖 pytest-asyncio。"""
    return asyncio.run(coro)


@pytest.fixture
def db(tmp_path):
    """创建独立的异步 SQLite 会话工厂，并写入一个测试用户。"""
    db_path = tmp_path / "test.db"
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_path.as_posix()}",
        poolclass=NullPool,
    )
    session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def setup():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with session_factory() as session:
            session.add(User(
                username="tester",
                email=TEST_EMAIL,
                password_hash=get_password_hash(TEST_PASSWORD),
            ))
            await session.commit()

    run(setup())

    yield engine, session_factory

    run(engine.dispose())


@pytest.fixture
def client(db, monkeypatch):
    """注入测试数据库并返回不触发 lifespan 的 TestClient。"""
    engine, session_factory = db

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    # ConversationService 直接使用模块级会话工厂，需要一并替换
    monkeypatch.setattr(conversation_service_module, "AsyncSessionLocal", session_factory)

    yield TestClient(app)  # 不使用 with，避免启动阶段编译真实 LangGraph 图

    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers():
    token = create_access_token(
        {"sub": TEST_EMAIL}, expires_delta=timedelta(minutes=30)
    )
    return {"Authorization": f"Bearer {token}"}
