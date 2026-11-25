"""核心工具、配置与状态图构建测试。"""
import asyncio

from jose import jwt

from app.core.config import settings
from app.core.hashing import get_password_hash, verify_password
from app.core.security import create_access_token
from app.lg_agent import lg_builder
from app.lg_agent.utils import new_uuid
from app.services.conversation_service import ConversationService
from app.services.llm_factory import LLMFactory
from main import safe_filename


def test_database_url_uses_configured_backend():
    assert settings.DATABASE_URL.startswith("sqlite+aiosqlite:///")
    assert settings.DATABASE_URL.endswith("kefu_agent.db")
    assert "llm_backend/llm_backend" not in settings.DATABASE_URL


def test_env_example_contains_no_real_credentials():
    """交付模板中不得保留原始配置里的明文密码。"""
    sample = (settings.GRAPHRAG_PROJECT_PATH.parents[1] / ".env.example").read_text("utf-8")
    assert "jjp0822_" not in sample
    assert "g1601522830" not in sample
    assert "change-me" in sample


def test_graphrag_project_path_is_resolved(tmp_path, monkeypatch):
    """相对路径基于项目根解析，且精简项目目录包含配置模板。"""
    path = settings.GRAPHRAG_PROJECT_PATH
    assert path.is_absolute()
    assert (path / "data" / "settings.yaml").is_file()
    assert (path / "data" / "prompts").is_dir()

    monkeypatch.setattr(settings, "GRAPHRAG_PROJECT_DIR", "graphrag_custom")
    assert settings.GRAPHRAG_PROJECT_PATH.name == "graphrag_custom"


def test_password_hash_and_verify():
    hashed = get_password_hash("correct horse")
    assert hashed != "correct horse"
    assert verify_password("correct horse", hashed) is True
    assert verify_password("wrong", hashed) is False


def test_access_token_can_be_decoded():
    token = create_access_token({"sub": "tester@example.com"})
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert payload["sub"] == "tester@example.com"
    assert "exp" in payload


def test_safe_filename_blocks_path_traversal():
    assert safe_filename("../../etc/passwd") == "passwd"
    assert safe_filename("C:\\tmp\\avatar.png") == "avatar.png"
    assert safe_filename("") == "file"


def test_conversation_title_is_normalized_and_truncated():
    assert ConversationService.get_conversation_title("  怎么  退货  ") == "怎么 退货"
    assert ConversationService.get_conversation_title("x" * 30) == "x" * 20 + "..."


def test_llm_factory_selects_service(monkeypatch):
    from app.services.deepseek_service import DeepseekService
    from app.services.ollama_service import OllamaService

    monkeypatch.setattr(settings, "CHAT_SERVICE", "deepseek")
    assert isinstance(LLMFactory.create_chat_service(), DeepseekService)

    monkeypatch.setattr(settings, "CHAT_SERVICE", "ollama")
    assert isinstance(LLMFactory.create_chat_service(), OllamaService)


def test_new_uuid_is_unique():
    assert new_uuid() != new_uuid()


def test_get_graph_builds_lazily_and_idempotently(tmp_path, monkeypatch):
    """图应在事件循环内创建，且重复调用返回同一实例。"""
    monkeypatch.setattr(lg_builder, "_CHECKPOINT_DB_PATH", tmp_path / "checkpoints.db")
    monkeypatch.setattr(lg_builder, "_graph", None)

    async def scenario():
        first = await lg_builder.get_graph()
        second = await lg_builder.get_graph()
        result = (first, second)
        await first.checkpointer.conn.close()
        return result

    first, second = asyncio.run(scenario())
    assert first is second
    assert (tmp_path / "checkpoints.db").exists()
