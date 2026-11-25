# 复盘（Reflection）

## 本次重构做了什么

**从 2168 个文件精简到 187 个文件**，其中绝大部分是 Microsoft GraphRAG 的 vendored 源码、LLM 响应缓存、测试数据和第三方 CI 配置。清理后仓库只保留：可运行后端、前端编译产物、精简版 GraphRAG 配置与提示词、脚本、测试、交付文档。

删除的主要类别：

- `app/graphrag/`：第三方库源码与缓存（约 66.5MB），改为 pip 依赖 + 项目级配置。
- `app/test/`：硬编码内网 IP / 密码的临时脚本，替换为 25 个独立 pytest 用例。
- `lg_builder_enhanced.py`、`lg_agent/main.py`、`eval/`、`planner/`、`ps_genai_agents/` 等无人引用的实验代码与空文件。
- 运行期 SQLite 数据库、checkpointer、上传样本、日志、IDE 配置与字节码缓存。
- README 中混入的另一个 Neo4j 示例项目章节。

## 修复的关键问题

1. **导入即崩溃**：`AsyncSqliteSaver` 在模块顶层创建，无事件循环时 `import main` 直接失败；改为 startup 阶段惰性编译图。
2. **路径双重拼接**：配置中的相对路径被重复拼成 `llm_backend/llm_backend/...`；统一为基于 `llm_backend/` 解析并兼容旧写法。
3. **GraphRAG 外部依赖**：vendored 导入 `app.graphrag.graphrag.*` 与已安装的 `graphrag` 包重复；改为按需导入外部包，启动导入从约 120s 降到约 16s。
4. **两处未定义变量**：`IndexingService.config_mapping` 与 Neo4j 连接失败后的 `neo4j_graph`，分别导致 `AttributeError` / `UnboundLocalError`。
5. **GraphRAG 查询失败二次异常**：`search_result["response"]` 改为 `.get()`，失败时返回空结果。
6. **静默异常**：搜索服务的 `except: pass` 改为记录日志并返回友好提示；建表脚本失败返回非零退出码。
7. **安全问题**：上传文件名路径穿越、`docker-compose.yml` 与 `.env.example` 中的明文密码、默认硬编码密码模板。
8. **破坏性脚本**：建表从 `drop_all + create_all` 改为幂等 `create_all`。

## 验证结果

- `python -m pytest -q --disable-warnings`：**25 passed**，所有需求验收标准与拒答规则都有对应用例。
- `python -m compileall -q .`：通过。
- `import main`：通过，注册 19 条路由。

## 已知限制

- **GraphRAG 真实索引/查询未在本机端到端跑通**：当前环境 `graphrag → spacy → thinc → torch` 链在加载 `torch/lib/c10.dll` 时失败。代码路径与配置已就绪，惰性导入保证主服务不受影响；需在依赖完整的环境补充联调。
- **文件问答仍是兜底回复**：`file-query` 意图没有真实 RAG 检索链路，这是明确的非目标。
- **默认 SQLite**：MySQL / Neo4j / Redis 属于可选能力，需要按 README 启动对应服务。
- **前端仅有编译产物**：Vue 3 源码不在仓库内，无法继续迭代界面。
- **JWT 默认密钥仍是占位符**：本地 `.env` 中已存在随机值，但新机器部署必须按 README 替换。

## 面试可讲述的切入点

- 为什么把第三方库从 vendored 改为 pip 依赖 + 项目级配置，如何权衡「可复现」与「仓库体积」。
- 异步框架中资源初始化时机的坑：为什么 `AsyncSqliteSaver` 必须在事件循环内创建，以及如何做到测试友好。
- 结构化意图路由 + 多工具子图的设计：如何让 LLM 在选择工具时拿到足够的参数约束。
- 权限边界设计：Token 为唯一用户身份来源，服务层再做一次归属过滤，避免越权。
- 用「需求—设计—测试」一一映射的方式证明功能可验证，而不是只展示可运行截图。
