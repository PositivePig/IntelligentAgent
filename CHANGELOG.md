# 更新日志

## [v4.0] - 2026-11-25 个人作品重构版

### 精简
- 删除 vendored Microsoft GraphRAG 源码、LLM 响应缓存与第三方 CI 配置（约 66.5MB / 1057 文件），改为 pip 依赖 + 精简配置目录 `graphrag_project/`。
- 删除无人引用的实验代码、评估脚本、空文件、硬编码内网地址的临时测试脚本。
- 清理运行期数据库、checkpointer、上传样本、日志、IDE 配置与字节码缓存。
- 重写 README，补齐 `docs/` 下 5 份交付文档。

### 修复
- `AsyncSqliteSaver` 改为在 FastAPI startup 阶段惰性创建，解决模块导入时 `no running event loop`。
- 统一配置路径解析，修复 `llm_backend/llm_backend/...` 重复拼接与旧机器绝对路径。
- GraphRAG 改为按需导入；启动导入耗时约 120s → 约 16s。
- 修复 `IndexingService.config_mapping` 未定义、`file_path` 未赋值、文件匹配正则未转义。
- 修复 Neo4j / GraphRAG 失败时的 `UnboundLocalError`、`KeyError` 与静默异常。
- 建表脚本改为幂等且失败时返回非零退出码；Neo4j 脚本修正模块搜索路径。
- 上传文件名做 basename 清洗，阻止路径穿越。
- 配置模板、docker-compose 与文档中的明文密码全部替换为占位符 / 环境变量。
- 缓存后台清理任务仅在事件循环内创建，避免构造服务时报错。

### 测试
- 新增 25 个自包含 pytest 用例，覆盖全部验收标准、REST 接口、拒答规则与外部依赖降级。

## [v3.0] - AssistGen 课程阶段

- 用户注册 / 登录 / JWT，会话创建、列表、改名与删除。
- DeepSeek V3 / R1 与 Ollama 流式问答、联网搜索、Redis 语义缓存。
- MySQL 会话持久化、GraphRAG 索引与知识图谱多工具查询。

## [v1.0] - 基础能力

- Ollama 本地部署与 REST API 接入。
- FastAPI 服务骨架与基础前端。
