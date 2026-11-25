# 需求规格（Spec）

## 项目定位

AssistGen 是一个可演示、可测试、可直接运行的**智能电商客服 Agent 个人作品**。仓库只包含后端服务、前端编译产物、精简版 GraphRAG 配置与交付文档，不包含学习资料、第三方库源码副本或运行时数据。

## 用户与场景

- 使用者：技术面试官、招聘方、本地开发者。
- 场景 1：启动服务后用 Vue 前端或 `/docs` 体验登录、流式问答与会话管理。
- 场景 2：运行 `pytest` 查看可复现的自动化测试，验证权限拒答与容错降级。
- 场景 3：用 `.env.example` 在另一台机器上复现部署，无需仓库内维护任何密钥。

## 功能需求

- FR-1 用户注册、登录与 JWT 鉴权。
- FR-2 普通问答、深度思考、联网搜索三类 SSE 流式接口。
- FR-3 会话创建、列表、改名、消息查询与删除，严格按用户隔离。
- FR-4 LangGraph 五意图路由（通用问答 / 补充追问 / 图片理解 / 文件兜底 / 知识图谱查询）。
- FR-5 知识图谱工具链：Text2Cypher、预定义 Cypher、GraphRAG 非结构化问答、联网检索。
- FR-6 Redis 语义缓存（按用户隔离、相似度阈值、TTL 清理）。
- FR-7 SQLite（默认，零安装）/ MySQL 双数据库后端，SQLite checkpointer 持久化 HITL 中断点。
- FR-8 文件上传与 GraphRAG 索引触发；图片上传与视觉模型分析。
- FR-9 Vue 3 编译产物由 FastAPI 托管，支持前端深链接刷新。

## 验收标准与测试映射

| 编号 | 验收标准 | 对应测试 |
|---|---|---|
| AC-01 | `GET /health` 返回 `{"status":"ok"}` | `test_health_check` |
| AC-02 | 注册、重复注册拒绝、登录成功/失败 | `test_register_login_and_duplicate_rejection` |
| AC-03 | 无 Token 访问业务接口一律 401 | `test_unauthenticated_requests_are_rejected`、`test_upload_image_requires_auth` |
| AC-04 | 伪造 Token 返回 401 | `test_invalid_token_is_rejected` |
| AC-05 | `/api/users/me` 返回当前用户信息 | `test_current_user_endpoint` |
| AC-06 | 会话 CRUD 正常，跨用户访问返回 403 | `test_conversation_crud_and_ownership_rejection` |
| AC-07 | `/api/chat` 以 SSE 流式返回，user_id 以 Token 为准 | `test_chat_stream_uses_token_user` |
| AC-08 | `/api/reason` 以 SSE 流式返回 | `test_reason_stream` |
| AC-09 | 上传文件名经路径穿越清洗后再落盘 | `test_upload_sanitizes_filename` |
| AC-10 | Vue 深链接刷新回退到 `index.html` | `test_spa_deep_link_falls_back_to_index` |
| AC-11 | SQLite 路径基于后端目录解析，不重复拼接 | `test_database_url_uses_configured_backend` |
| AC-12 | 交付模板不含原始明文密码 | `test_env_example_contains_no_real_credentials` |
| AC-13 | GraphRAG 目录可解析且配置模板/提示词存在 | `test_graphrag_project_path_is_resolved` |
| AC-14 | 密码哈希校验正确 | `test_password_hash_and_verify` |
| AC-15 | JWT 可创建并解码出用户标识与过期时间 | `test_access_token_can_be_decoded` |
| AC-16 | 上传文件名清洗函数覆盖 `../` 与 Windows 路径 | `test_safe_filename_blocks_path_traversal` |
| AC-17 | 会话标题归一化并截断 | `test_conversation_title_is_normalized_and_truncated` |
| AC-18 | LLM 工厂按配置切换 DeepSeek / Ollama | `test_llm_factory_selects_service` |
| AC-19 | 线程 ID 唯一 | `test_new_uuid_is_unique` |
| AC-20 | 状态图在事件循环中惰性创建且幂等 | `test_get_graph_builds_lazily_and_idempotently` |
| AC-21 | 空任务被 Text2Cypher 节点拒绝为结构化错误 | `test_cypher_node_rejects_empty_task` |
| AC-22 | Neo4j 连接失败时节点降级而非抛异常 | `test_cypher_node_handles_neo4j_failure` |
| AC-23 | GraphRAG 查询失败时返回空结果而非 KeyError | `test_graphrag_node_returns_empty_result_on_failure` |
| AC-24 | 索引服务配置文件解析不依赖未定义属性 | `test_indexing_service_helpers` |

## 非目标（任何文件均不得实现）

- N-1 不提供 Vue 3 前端源码，仅保留编译产物 `llm_backend/static/dist/`。
- N-2 不实现真实的文件问答 RAG 链路；`file-query` 仅返回友好提示。
- N-3 不把 Microsoft GraphRAG 第三方源码或 LLM 响应缓存副本 vendored 进仓库，改用 `requirements.txt` 声明依赖。
- N-4 不实现本地 FAISS 知识库问答（旧版 baseline 已移除，统一走 Neo4j + GraphRAG）。
- N-5 不在仓库中提交任何真实 API Key、数据库密码或运行期 SQLite/检查点数据。
- N-6 不实现多租户计费、工单系统或客服人工坐席转接。

## 运行环境

- Python 3.12；依赖见 `requirements.txt` / `environment.yml`。
- 默认使用 SQLite，MySQL / Neo4j / Redis 仅在对应功能需要时启动（可用 `docker-compose.yml`）。
- GraphRAG 索引与查询为可选能力，需要可用的 OpenAI 兼容端点与完整依赖链。
