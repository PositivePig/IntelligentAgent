# 系统设计（Design）

## 总体架构

```
Vue 3 编译产物 (static/dist)
        │ HTTP / SSE
        ▼
FastAPI (llm_backend/main.py)
   ├── /api/auth*           注册 / 登录 / JWT 鉴权
   ├── /api/chat|reason|search   LLMFactory → DeepSeek / Ollama 流式服务
   ├── /api/upload|upload/image  文件落盘 + GraphRAG 索引 / 图片保存
   ├── /api/conversations*       ConversationService → SQLite / MySQL
   └── /api/langgraph/query|resume
                ▼
        LangGraph Agent (app/lg_agent/lg_builder.py)
        START → analyze_and_route_query（结构化意图分类）
          ├─ general-query     → respond_to_general_query
          ├─ additional-query  → get_additional_info（范围检查 + 追问）
          ├─ image-query       → create_image_query（视觉模型 → PIL 压缩 → 客服口吻回复）
          ├─ file-query        → create_file_query（友好兜底）
          └─ graphrag-query    → create_research_plan
                     └─ KG 多工具子图：Guardrails → Planner → Tool Selection
                        → Text2Cypher / Predefined Cypher / GraphRAG / 联网检索
                        → Summarize → Final Answer
        checkpointer = AsyncSqliteSaver（startup 阶段惰性创建）
```

## 目录职责

| 目录 | 职责 |
|---|---|
| `app/api/` | 认证路由 |
| `app/core/` | 配置、数据库会话、密码哈希、JWT、日志、中间件 |
| `app/models/`、`app/schemas/` | ORM 模型与 Pydantic 请求/响应模型 |
| `app/services/` | LLM 工厂、DeepSeek/Ollama 服务、搜索、会话、用户、语义缓存、GraphRAG 索引 |
| `app/tools/`、`app/prompts/` | 搜索工具定义与提示词 |
| `app/lg_agent/` | LangGraph 主图、状态、提示词、知识图谱子图 |
| `graphrag_project/data/` | GraphRAG 配置模板与中文提示词（不含第三方源码、不含缓存） |
| `scripts/` | 幂等建表脚本、Neo4j 示例数据导入脚本 |
| `tests/` | 独立可运行的 pytest 用例，不依赖外部服务 |

## 关键设计决策

1. **第三方依赖外部化**：GraphRAG 由 pip 声明；仓库只保留项目级配置与提示词。首次使用时惰性导入，启动导入耗时由约 120s 降到约 16s。
2. **异步资源在事件循环内创建**：`AsyncSqliteSaver` 要求运行中的 loop，因此状态图通过 `get_graph()` 在 FastAPI startup 中编译，模块导入阶段不再抛 `RuntimeError`。
3. **鉴权单一事实来源**：所有业务接口的 `user_id` 来自 JWT，请求体中的同名字段仅为兼容保留；跨用户资源访问由服务层二次过滤。
4. **失败降级**：Neo4j / GraphRAG 不可用时返回结构化错误或空结果，不中断 SSE 流；搜索服务异常记录日志并返回友好提示。
5. **零安装默认**：默认 SQLite + 相对路径；`.env.example` 中只放占位符，真实 `.env` 被 `.gitignore` 排除。

## 对外接口与核心函数测试对照

| 接口 / 函数 | 测试 |
|---|---|
| `GET /health` | `test_health_check` |
| `POST /api/register` | `test_register_login_and_duplicate_rejection` |
| `POST /api/token` | `test_register_login_and_duplicate_rejection` |
| `GET /api/users/me` | `test_current_user_endpoint`、`test_invalid_token_is_rejected` |
| `POST /api/chat` | `test_chat_stream_uses_token_user`、`test_unauthenticated_requests_are_rejected` |
| `POST /api/reason` | `test_reason_stream`、`test_unauthenticated_requests_are_rejected` |
| `POST /api/search` | `test_unauthenticated_requests_are_rejected` |
| `POST /api/upload` | `test_upload_sanitizes_filename` |
| `POST /api/upload/image` | `test_upload_image_requires_auth` |
| `POST /api/conversations` | `test_conversation_crud_and_ownership_rejection` |
| `GET /api/conversations/user/{user_id}` | `test_conversation_crud_and_ownership_rejection` |
| `GET /api/conversations/{id}/messages` | `test_conversation_crud_and_ownership_rejection` |
| `DELETE /api/conversations/{id}` | `test_conversation_crud_and_ownership_rejection` |
| `PUT /api/conversations/{id}/name` | `test_conversation_crud_and_ownership_rejection` |
| `POST /api/langgraph/query` | `test_unauthenticated_requests_are_rejected` |
| `POST /api/langgraph/resume` | `test_unauthenticated_requests_are_rejected` |
| SPA 404 回退处理器 | `test_spa_deep_link_falls_back_to_index` |
| `Settings.DATABASE_URL` / `GRAPHRAG_PROJECT_PATH` | `test_database_url_uses_configured_backend`、`test_graphrag_project_path_is_resolved` |
| `safe_filename` | `test_safe_filename_blocks_path_traversal`、`test_upload_sanitizes_filename` |
| `get_password_hash` / `verify_password` | `test_password_hash_and_verify` |
| `create_access_token` / `get_current_user` | `test_access_token_can_be_decoded`、全部鉴权拒答测试 |
| `ConversationService.get_conversation_title` | `test_conversation_title_is_normalized_and_truncated` |
| `LLMFactory.create_chat_service` | `test_llm_factory_selects_service` |
| `new_uuid` | `test_new_uuid_is_unique` |
| `get_graph` | `test_get_graph_builds_lazily_and_idempotently` |
| `create_cypher_query_node` | `test_cypher_node_rejects_empty_task`、`test_cypher_node_handles_neo4j_failure` |
| `create_graphrag_query_node` | `test_graphrag_node_returns_empty_result_on_failure` |
| `IndexingService._get_config_file` / `_get_file_type` | `test_indexing_service_helpers` |
| `.env.example` 脱敏约定 | `test_env_example_contains_no_real_credentials` |

## 拒答规则

| 编号 | 规则 | 期望行为 | 对应测试 |
|---|---|---|---|
| R-1 | 业务接口缺少 Bearer Token | 401 `Could not validate credentials` | `test_unauthenticated_requests_are_rejected`、`test_upload_image_requires_auth` |
| R-2 | Token 伪造或已失效 | 401 | `test_invalid_token_is_rejected` |
| R-3 | 访问其他用户的会话/消息 | 403 `无权访问其他用户的会话` | `test_conversation_crud_and_ownership_rejection` |
| R-4 | Text2Cypher 节点收到空任务 | 返回结构化错误，不调用模型 | `test_cypher_node_rejects_empty_task` |
| R-5 | Neo4j 或 GraphRAG 不可用 | 返回降级结果，不中断工作流 | `test_cypher_node_handles_neo4j_failure`、`test_graphrag_node_returns_empty_result_on_failure` |
| R-6 | 上传文件名含路径分隔符 | 只保留 basename 后落盘 | `test_upload_sanitizes_filename` |
