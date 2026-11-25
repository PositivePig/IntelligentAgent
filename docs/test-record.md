# 测试记录（Test Record）

## 执行环境

- 日期：2026-11-25
- Python 3.12.13（conda 环境 `deepseek_agent`）
- 执行命令：在 `llm_backend/` 下运行 `python -m pytest -q --disable-warnings`
- 结果：**25 passed**，耗时约 20s（含一次约 16s 的模块导入）
- 测试隔离：每个用例使用独立临时 SQLite 文件，不连接 MySQL / Neo4j / Redis / 大模型 API

## 用例清单

| 用例 ID | 测试函数 | 覆盖目标 | 状态 |
|---|---|---|---|
| TC-01 | `test_health_check` | AC-01 健康检查 | 通过 |
| TC-02 | `test_register_login_and_duplicate_rejection` | AC-02 注册/登录/重复拒绝 | 通过 |
| TC-03 | `test_unauthenticated_requests_are_rejected` | AC-03、R-1 六类接口未授权拒答 | 通过 |
| TC-04 | `test_upload_image_requires_auth` | AC-03、R-1 图片上传拒答 | 通过 |
| TC-05 | `test_invalid_token_is_rejected` | AC-04、R-2 伪造 Token | 通过 |
| TC-06 | `test_current_user_endpoint` | AC-05 当前用户 | 通过 |
| TC-07 | `test_conversation_crud_and_ownership_rejection` | AC-06、R-3 会话 CRUD 与 403 | 通过 |
| TC-08 | `test_chat_stream_uses_token_user` | AC-07 SSE 与 Token 优先 | 通过 |
| TC-09 | `test_reason_stream` | AC-08 深度思考 SSE | 通过 |
| TC-10 | `test_upload_sanitizes_filename` | AC-09、R-6 路径穿越清洗 | 通过 |
| TC-11 | `test_spa_deep_link_falls_back_to_index` | AC-10 前端深链接回退 | 通过 |
| TC-12 | `test_database_url_uses_configured_backend` | AC-11 SQLite 路径解析 | 通过 |
| TC-13 | `test_env_example_contains_no_real_credentials` | AC-12 配置脱敏 | 通过 |
| TC-14 | `test_graphrag_project_path_is_resolved` | AC-13 GraphRAG 目录解析 | 通过 |
| TC-15 | `test_password_hash_and_verify` | AC-14 密码哈希 | 通过 |
| TC-16 | `test_access_token_can_be_decoded` | AC-15 JWT 编解码 | 通过 |
| TC-17 | `test_safe_filename_blocks_path_traversal` | AC-16 文件名清洗边界 | 通过 |
| TC-18 | `test_conversation_title_is_normalized_and_truncated` | AC-17 标题生成 | 通过 |
| TC-19 | `test_llm_factory_selects_service` | AC-18 模型工厂切换 | 通过 |
| TC-20 | `test_new_uuid_is_unique` | AC-19 线程 ID | 通过 |
| TC-21 | `test_get_graph_builds_lazily_and_idempotently` | AC-20 状态图惰性初始化 | 通过 |
| TC-22 | `test_cypher_node_rejects_empty_task` | AC-21、R-4 空任务拒答 | 通过 |
| TC-23 | `test_cypher_node_handles_neo4j_failure` | AC-22、R-5 Neo4j 降级 | 通过 |
| TC-24 | `test_graphrag_node_returns_empty_result_on_failure` | AC-23、R-5 GraphRAG 降级 | 通过 |
| TC-25 | `test_indexing_service_helpers` | AC-24 索引配置解析 | 通过 |

## 拒答规则专项结果

设计文档 R-1 ~ R-6 均已覆盖并通过：

- R-1：6 个业务接口 + 图片上传共 7 条未授权请求全部返回 401（`test_unauthenticated_requests_are_rejected`、`test_upload_image_requires_auth`）。
- R-2：伪造 Token 返回 401（`test_invalid_token_is_rejected`）。
- R-3：另一用户访问会话列表与消息返回 403（`test_conversation_crud_and_ownership_rejection`）。
- R-4：空任务由 Text2Cypher 节点返回 `validate_input` 错误状态（`test_cypher_node_rejects_empty_task`）。
- R-5：Neo4j 连接失败、GraphRAG 查询失败均返回结构化降级结果且无未捕获异常（TC-23、TC-24）。
- R-6：`../../evil.txt` 上传后文件名归一化为 `evil.txt`，落盘路径不含 `..`（TC-10）。

## 未执行项与原因

- **真实 GraphRAG 索引/查询**：本环境 `graphrag 2.1.0` 的导入链会加载 `spacy → thinc → torch`，而 `torch/lib/c10.dll` 无法初始化（Windows 动态链接库错误）。因此只测试了降级路径与配置解析；惰性导入保证该依赖缺失时主服务仍可启动。
- **真实大模型调用 / Neo4j 查询 / Redis 缓存命中**：需要外部服务与密钥，不属于本地回归测试范围；端到端联调需在有服务的环境手动执行。
- **pytest-asyncio**：当前环境未安装，测试通过 `asyncio.run()` 执行异步场景，因此不依赖该插件。

## 修复前后对比（同一套测试）

| 缺陷 | 修复前 | 修复后 |
|---|---|---|
| 模块导入即创建 `AsyncSqliteSaver` | `RuntimeError: no running event loop`，无法导入 `main` | startup 惰性编译，导入成功 |
| `GRAPHRAG_PROJECT_DIR` 指向旧机器绝对路径 | 解析失败 | 统一基于 `llm_backend/` 解析，路径可复现 |
| `IndexingService.config_mapping` 未定义 | 调用即 `AttributeError` | 已初始化，配置解析测试通过 |
| Neo4j 连接失败后使用未赋值变量 | `UnboundLocalError` | 返回结构化错误 |
| GraphRAG 查询失败访问 `search_result["response"]` | `KeyError` | 返回空字符串 |
| 无事件循环时构造 DeepSeek 服务 | `RuntimeError` | 跳过后台清理任务创建 |
| 上传文件名可含路径分隔符 | 可穿越到任意目录 | 只保留 basename |
