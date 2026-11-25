from pydantic_settings import BaseSettings
from enum import Enum
from pathlib import Path

# ROOT_DIR 指向 llm_backend/（.env 与 data/ 均在此），PROJECT_ROOT 指向项目根
ROOT_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = ROOT_DIR.parent
ENV_FILE = ROOT_DIR / ".env"


def _resolve_backend_path(raw: str) -> Path:
    """兼容新旧两种相对路径写法，统一基于 llm_backend/ 解析。"""
    path = Path(raw).expanduser()
    if path.is_absolute():
        return path
    normalized = path.as_posix().removeprefix("llm_backend/")
    return ROOT_DIR / normalized

class ServiceType(str, Enum):
    DEEPSEEK = "deepseek"
    OLLAMA = "ollama"

class Settings(BaseSettings):
    # Deepseek settings
    DEEPSEEK_API_KEY: str
    DEEPSEEK_BASE_URL: str
    DEEPSEEK_MODEL: str
    
    # Vision Model settings (独立配置)
    VISION_API_KEY: str
    VISION_BASE_URL: str
    VISION_MODEL: str
    
    # Ollama settings
    OLLAMA_BASE_URL: str
    OLLAMA_CHAT_MODEL: str
    OLLAMA_REASON_MODEL: str
    OLLAMA_EMBEDDING_MODEL: str
    OLLAMA_AGENT_MODEL: str
    # Service selection
    CHAT_SERVICE: ServiceType = ServiceType.DEEPSEEK
    REASON_SERVICE: ServiceType = ServiceType.OLLAMA
    AGENT_SERVICE: ServiceType = ServiceType.DEEPSEEK
    
    # Search settings
    SERPAPI_KEY: str
    SEARCH_RESULT_COUNT: int = 3
    
    # Database settings
    # DB_TYPE: "mysql" 使用 MySQL（需安装并运行 MySQL 服务）；"sqlite" 使用本地文件数据库（零安装，开箱即用）
    DB_TYPE: str = "sqlite"
    DB_HOST: str
    DB_PORT: int
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str
    # SQLite 数据库文件路径（仅当 DB_TYPE=sqlite 时使用）
    SQLITE_PATH: str = "data/kefu_agent.db"
    
    # Neo4j settings
    NEO4J_URL: str = "bolt://localhost:7687"
    NEO4J_USERNAME: str = "neo4j"
    NEO4J_PASSWORD: str = "password"
    NEO4J_DATABASE: str = "neo4j"
    
    # JWT settings
    SECRET_KEY: str = "your-secret-key"  # 在生产环境中使用安全的密钥
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Redis settings
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""
    REDIS_CACHE_EXPIRE: int = 3600
    REDIS_CACHE_THRESHOLD: float = 0.8
    
    # Embedding settings 
    EMBEDDING_TYPE: str = "ollama"  # ollama 或 sentence_transformer
    EMBEDDING_MODEL: str = "bge-m3"  # ollama embedding模型
    EMBEDDING_THRESHOLD: float = 0.90  # 语义相似度阈值
    
    # GraphRAG settings
    GRAPHRAG_PROJECT_DIR: str = "graphrag_project"  # 相对 llm_backend/
    GRAPHRAG_EMBEDDING_MODEL: str = "text-embedding-3-small"    # 索引用嵌入模型
    GRAPHRAG_DATA_DIR: str = "data"                             # 数据目录名称
    GRAPHRAG_QUERY_TYPE: str = "local"                      # 查询类型
    GRAPHRAG_RESPONSE_TYPE: str = "text"                    # 响应类型
    GRAPHRAG_COMMUNITY_LEVEL: int = 3                       # 社区级别
    GRAPHRAG_DYNAMIC_COMMUNITY: bool = False                # 是否动态选择社区
    
    @property
    def DATABASE_URL(self) -> str:
        if self.DB_TYPE.lower() == "sqlite":
            # SQLite 路径支持绝对路径；若为相对路径则基于项目根目录解析
            path = _resolve_backend_path(self.SQLITE_PATH)
            # 确保所在目录存在
            path.parent.mkdir(parents=True, exist_ok=True)
            return f"sqlite+aiosqlite:///{path.as_posix()}"
        # 默认 MySQL（异步驱动 aiomysql）
        return f"mysql+aiomysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def GRAPHRAG_PROJECT_PATH(self) -> Path:
        """解析 GraphRAG 项目目录。相对路径一律基于项目根，避免重复拼接。"""
        return _resolve_backend_path(self.GRAPHRAG_PROJECT_DIR)

    @property
    def REDIS_URL(self) -> str:
        """构建Redis URL"""
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    @property
    def NEO4J_CONN_URL(self) -> str:
        """构建Neo4j连接URL"""
        return f"{self.NEO4J_URL}"
    
    class Config:
        env_file = str(ENV_FILE)  # 使用绝对路径
        env_file_encoding = "utf-8"
        case_sensitive = True

settings = Settings() 