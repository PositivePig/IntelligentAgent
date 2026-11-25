# AssistGen — 智能电商客服 Agent

一个可运行、可测试的个人作品：FastAPI + LangGraph + 知识图谱 + 语义缓存的电商客服系统。仓库包含后端源码、Vue 3 编译产物、精简版 GraphRAG 配置与完整交付文档，**不含第三方库源码副本、运行时数据和任何真实密钥**。

## 功能亮点

- **五意图路由**：LangGraph 将用户问题分为通用问答、补充追问、图片理解、文件兜底、知识图谱查询。
- **多工具 KG 子图**：Guardrails → Planner → Tool Selection → Text2Cypher / 预定义 Cypher / GraphRAG / 联网检索 → Summarize → Final Answer。
- **多模型热切换**：`LLMFactory` 按配置在 DeepSeek 与 Ollama 之间切换，两套服务实现同一流式接口。
- **人机确认可恢复**：`AsyncSqliteSaver` 把中断点持久化到 SQLite，服务重启后仍可继续。
- **Redis 语义缓存**：Ollama 向量化 + 余弦相似度阈值命中，按用户隔离并带 TTL 清理。
- **权限边界**：所有业务接口以 JWT 为唯一用户身份来源，服务层再做一次归属过滤。
- **25 个自包含测试**：不依赖外部服务即可验证接口、拒答规则与容错降级。

## 快速开始

```bash
# 1. 准备环境（Python 3.12）
conda env create -f environment.yml
conda activate deepseek_agent
# 或使用 pip：pip install -r requirements.txt

# 2. 复制配置模板并填写自己的密钥
cp .env.example llm_backend/.env
# Windows: copy .env.example llm_backend\.env

# 3. 初始化 SQLite 表（幂等，不会删除已有数据）
cd llm_backend
python scripts/init_db.py

# 4. 启动服务
python run.py
```

启动后：

- 前端界面：<http://localhost:8000>
- API 文档：<http://localhost:8000/docs>
- 健康检查：<http://localhost:8000/health>

可选中间件：`docker compose up -d` 启动 MySQL / Neo4j / Redis，然后把 `.env` 中 `DB_TYPE` 改为 `mysql`。Neo4j 示例数据可用 `python scripts/init_neo4j.py` 导入。

服务启动参数支持 `HOST` / `PORT` / `RELOAD` / `LOG_LEVEL` 环境变量，默认值分别为 `0.0.0.0` / `8000` / `true` / `error`。

## 测试

```bash
cd llm_backend
python -m pytest -q --disable-warnings
```

当前结果：**25 passed**。测试使用临时 SQLite 数据库与 stub 服务，不调用外部 API。需求验收标准、接口与拒答规则的逐条对应关系见 `docs/spec.md`、`docs/design.md` 和 `docs/test-record.md`。

## 项目结构

```text
deepseek_agent/
├── .env.example                 # 配置模板（仅占位符）
├── .gitignore
├── CHANGELOG.md
├── README.md
├── docker-compose.yml           # 可选中间件，密码由环境变量注入
├── environment.yml
├── requirements.txt
├── docs/
│   ├── spec.md                  # 需求与验收标准
│   ├── design.md                # 架构、接口与拒答规则
│   ├── test-record.md           # 测试结果与未执行项
│   ├── ai-log.md                # AI 建议与人工判断记录
│   └── reflection.md            # 重构复盘与已知限制
└── llm_backend/
    ├── .env                     # 本地真实配置（已 gitignore，不随仓库交付）
    ├── main.py                  # FastAPI 应用与全部路由
    ├── run.py                   # uvicorn 启动入口
    ├── pytest.ini
    ├── app/
    │   ├── api/                 # 注册 / 登录 / 当前用户
    │   ├── core/                # 配置、数据库、密码、JWT、日志、中间件
    │   ├── lg_agent/            # LangGraph 主图与知识图谱子图
    │   ├── models/              # User / Conversation / Message ORM
    │   ├── prompts/             # 搜索提示词
    │   ├── schemas/             # Pydantic 请求响应模型
    │   ├── services/            # LLM 工厂、搜索、会话、缓存、索引等
    │   └── tools/               # 检索工具与函数定义
    ├── data/                    # SQLite / checkpointer 运行数据（gitignore）
    ├── graphrag_project/        # GraphRAG 配置模板与中文提示词
    │   └── data/                # settings.yaml、prompts/、prompt_turn_output/ 等
    ├── logs/                    # 运行日志（gitignore）
    ├── scripts/                 # init_db.py、init_neo4j.py
    ├── static/dist/             # Vue 3 编译产物，由 FastAPI 托管
    ├── tests/                   # conftest.py、test_api.py、test_agent.py、test_core.py
    └── uploads/                 # 上传文件（gitignore）
```

## 技术栈

- 后端：FastAPI、SQLAlchemy 2.x（aiosqlite / aiomysql）、Pydantic v2、python-jose
- Agent：LangGraph 0.3、LangChain DeepSeek / Ollama / Neo4j
- 检索：Neo4j + Text2Cypher、Microsoft GraphRAG 2.1（外部依赖）、SerpAPI
- 缓存：Redis + Ollama Embedding
- 前端：Vue 3 + Element Plus（仅编译产物）

## 部署注意事项

1. 把 `.env` 中的 `SECRET_KEY` 换成随机长字符串，所有 `change-me` / `sk-your-*` 占位符都要替换。
2. 生产环境关闭 `RELOAD`，按实际域名收紧 CORS，并启用 HTTPS。
3. GraphRAG 索引与查询需要可用的 OpenAI 兼容端点和完整依赖链；当前环境缺少可用的 torch 动态库，真实索引查询未端到端验证，但主服务不受影响（惰性导入）。
4. 仓库不应提交 `.env`、`*.db`、`logs/`、`uploads/` 和 GraphRAG 生成目录。

## License

MIT
