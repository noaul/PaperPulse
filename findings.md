# 发现与决策

## 需求
- 用户认为当前 PaperPulse 代码太简单，希望重构成更复杂、更工程化的项目。
- 保留当前前端页面使用方式，允许更美观。
- Docker 相关任务必须先本地部署验证，用户看完确认后再推送 GitHub 和部署 nc48。

## 研究发现
- 当前工作区干净：`main...origin/main`。
- 当前提交：`cfda1c1 fix: allow health checks without auth`。
- 当前后端已有模型：Feed、Paper、Keyword、AnalysisResult、Setting。
- 当前后端接口已覆盖 feeds、papers、keywords、settings、analysis、dashboard、auth。
- 数据库使用 SQLAlchemy async + SQLite，启动时通过 `Base.metadata.create_all` 自动建表，新增模型可在现有部署中直接创建新表。
- 当前定时任务 `daily_job()` 直接串联 `fetch_all_feeds`、`analyze_new_papers`、`send_daily_report`、`export_data`，适合作为第一轮 workflow 编排入口。
- 当前手动分析接口 `/api/analysis/run`、`/api/analysis/fetch-and-analyze`、`/api/analysis/send-report` 返回结构简单，必须保持兼容。
- 前端 API 封装集中在 `frontend/src/api/index.ts`，Dashboard 是最小侵入的执行状态展示位置。
- 本地 Docker 直连 Docker Hub 不稳定，需使用本机 `127.0.0.1:18080` 代理环境变量完成基础镜像拉取和构建。
- 本地容器验证地址：`http://127.0.0.1:18095`，当前容器 `paperpulse` 为 healthy。
- 新增 execution API 已验证可返回执行摘要与节点日志，手动旧分析接口也会生成 execution 记录。
- `/api/analysis` 原先后端返回 list、前端按分页对象使用，已改为分页响应。
- ScienceDirect 等 RSS 源可能把摘要/元信息放在 `summary`/`description`/`content` 且带 HTML；需要抓取时和输出时都做文本清理。
- 邮件发送原先只支持 STARTTLS，465 端口需要 SMTP_SSL；发送结果需要返回具体原因便于前端提示。
- ScienceDirect RSS 原文链接会带 `dgcid=rss_sd_all` 跟踪参数；论文入库、列表输出、分析输出、邮件链接需要统一做 URL 归一化，移除 `dgcid`/`utm_*` 等跟踪参数，同时保留正常业务查询参数。
- 文献抓取+分析场景下，用户期望进度“总数”表示本次新抓取论文数，而不是数据库里全部待分析论文数；因此 workflow 需要把抓取节点产出的论文 ID 传给分析节点。
- 分析暂停/取消只能做协作式控制：正在进行的单篇 AI HTTP 请求不能安全中断，但可以在每篇论文前后检查控制状态；暂停时后台任务等待，取消时停止后续论文并将执行记录标记为 `cancelled`。
- 2026-05-11 再次盘点：当前远端已是最新，工作区干净，当前本地最新提交为 `2ad5ec5 docs: add project planning notes`。
- 当前仓库中 `task_plan.md`、`findings.md`、`progress.md` 已被 Git 跟踪，和备注“不应进入最终提交”不一致；本轮继续维护这些文件作为项目工作台，不做无关清理。
- 后端当前架构：FastAPI + SQLAlchemy async + SQLite + APScheduler + workflow engine；核心模型有 Feed、Paper、Keyword、AnalysisResult、WorkflowExecution、WorkflowExecutionLog、Setting。
- 前端当前架构：Vue 3 + Vue Router + Pinia + Axios + Tailwind；页面有 Dashboard、Feeds、Papers、Analysis、Keywords、Settings、Login。
- 当前没有前端测试脚本；后端测试是 unittest，测试文件位于 `backend/tests`，Docker 镜像内依赖环境更完整。
- `backend/static` 中存在构建产物，当前 `.gitignore` 未忽略 `backend/static`；如果继续提交构建产物，需要明确这是项目发布策略，否则建议后续规范化。
- 当前数据库结构仍依赖 `Base.metadata.create_all`，未引入 Alembic；后续新增报告中心、任务队列、知识库同步会让迁移管理成为工程化升级的关键点。
- 阶段 10 的“报告中心与 WeKnora 联动”仍未实现，是全面升级中最自然的第一批高价值功能。

## 技术决策
| 决策 | 理由 |
|------|------|
| 新增 WorkflowExecution/WorkflowExecutionLog | 让抓取、分析、邮件、备份可观测，而不是黑盒操作 |
| 旧 analysis API 复用 workflow engine | 保持前端兼容，并提升内部架构 |
| 前端只增强 Dashboard/状态展示 | 不改变用户已经熟悉的页面路径 |
| 使用容器内 unittest 验证 workflow engine | 本地 Python 缺后端依赖，Docker 镜像具备完整依赖环境 |
| 分析结果独立为 `/analysis` 页面 | Dashboard 保持操作和进度，分析页面专注浏览结果 |
| 邮件报告包含论文摘要 | 用户明确要求不只题目，也要有摘要 |
| 后续优先做“报告中心 + 摘要增强 + 邮件预览/重发” | 这是论文抓取→分析→汇总→通知闭环里最缺的可见性和可控性 |
| 报告中心使用数据库持久化 Report/ReportItem/EmailDelivery | 页面刷新后仍可查看已生成报告、Markdown 和投递状态，解决一次性邮件/内存态结果不可追踪的问题 |
| `send_daily_report()` 委托报告中心服务 | 保留旧 analysis/workflow 入口兼容，同时让定时邮件也自动生成可追溯报告 |

## 后续功能复杂度分析

复杂度按影响面评估：S=半天内，M=1-2天，L=3-5天，XL=需要分阶段。

| 功能 | 用户价值 | 复杂度 | 主要改动 | 风险 |
|------|---------|--------|----------|------|
| 报告中心：保存每日/手动分析报告，可查看、预览、重发邮件 | 高 | M | 新增 Report/ReportItem 模型、API、页面 | 邮件内容和分析结果去重 |
| 摘要增强：RSS 无真实摘要时二次抓取原文页/Crossref/OpenAlex 补摘要 | 高 | M-L | 新增 metadata/abstract enrichment service 和缓存字段 | 不同站点结构差异、网络失败 |
| 邮件预览与发送记录：发送前预览、发送后记录状态/错误/重试 | 高 | M | EmailDelivery 模型、预览 API、重试按钮 | SMTP 错误多样 |
| 分析结果增强：搜索、排序、按主题词/期刊筛选、CSV/Markdown 导出 | 中高 | S-M | 扩展 analysis API 和 Analysis 页面 | 查询性能 |
| 论文详情页：单篇论文完整摘要、AI 解释、相关主题词、原文链接 | 中高 | S-M | 前端详情页/弹窗，后端详情接口增强 | UI 信息密度 |
| 工作流运行页：独立查看所有工作流、重试、取消、日志筛选 | 中高 | M | 扩展 execution API，新增页面 | 后台任务取消需要状态管理 |
| 任务队列：分析任务排队、并发限制、失败重试 | 高 | L | 引入任务状态机/队列服务 | 与当前 FastAPI background task 迁移 |
| 趋势分析：按周/月统计主题词热度、期刊分布、相关论文趋势图 | 中高 | M-L | 聚合 API、图表组件 | 前端图表依赖 |
| AI 文献综述：按主题词生成日报/周报综述和研究趋势总结 | 高 | L | Report generation workflow、AI 聚合提示词 | Token 成本、长上下文截断 |
| 向量检索/RAG：按自然语言检索历史论文和分析结果 | 高 | L-XL | Embedding、向量库/SQLite 扩展、检索页面 | 依赖和部署复杂度 |
| PDF/全文解析：下载 PDF 并提取全文，补充摘要和方法/结论 | 高 | XL | PDF 下载、解析、存储、版权/失败处理 | 站点权限、文件体积、解析质量 |
| 数据库迁移：Alembic 管理表结构演进 | 工程价值高 | M | 引入 migrations，启动迁移流程 | 现有 SQLite 数据兼容 |
| 多用户/权限：不同用户的订阅源、关键词、报告隔离 | 中 | L | Auth/DB 关联重构 | 现有数据迁移 |

## 推荐下一轮实施范围

优先级建议：
1. **报告中心 + 邮件预览/重发**：最贴近当前邮件问题，能让用户确认“发了什么、为什么没发、能不能重发”。
2. **分析结果增强**：搜索/筛选/导出，提升已分析数据的使用价值。
3. **摘要增强服务**：解决 RSS 只有元信息、没有真实 abstract 的问题。
4. **工作流运行页**：把当前 Dashboard 里的工作流信息独立出来，提升工程化观感。
5. **AI 文献综述**：在报告中心稳定后做，可以生成真正的“文献汇总报告”。

## 全面升级候选路线图（阶段 13）

| 模块 | 目标 | 价值 | 复杂度 | 建议批次 |
|------|------|------|--------|----------|
| 报告中心 | 保存每日/手动报告，支持预览、查看、重发、Markdown 导出 | 高 | M | P0 |
| 邮件投递记录 | 记录每次发送内容、收件人、状态、错误、重试入口 | 高 | M | P0 |
| 数据库迁移 | 引入 Alembic 或等价迁移层，管理 SQLite schema 演进 | 高 | M | P0/P1 |
| 工作流运行页 | 独立页面展示 executions、日志筛选、重试、取消 | 中高 | M | P1 |
| 摘要增强 | 对 RSS 摘要不足的论文补充 Crossref/OpenAlex/页面元数据 | 高 | M-L | P1 |
| 分析增强 | 分析结果搜索、批量导出、按期刊/关键词/时间聚合 | 中高 | S-M | P1 |
| AI 文献综述 | 基于当日报告/主题生成综述与趋势总结 | 高 | L | P2 |
| WeKnora 同步 | 将报告和高相关论文以 Markdown 同步到知识库 | 中高 | M-L | P2 |
| RAG/语义检索 | 对历史论文和报告做向量检索/问答 | 高 | L-XL | P3 |
| 多用户/权限 | 用户级订阅源、关键词、报告隔离 | 中 | L | P3 |

## P0 报告中心实现发现

- `Base.metadata.create_all` 会在启动时自动创建 `reports`、`report_items`、`email_deliveries` 三张新表，适合当前 SQLite 部署方式。
- 本地挂载数据库 `data/paperpulse.db` 已验证新表创建成功。
- 本地 API 验证结果：
  - `GET /reports`：SPA 路由 200。
  - `GET /api/reports`：认证后返回报告列表。
  - `POST /api/reports`：阈值 8.0 生成报告成功，生成 31 条报告项。
  - `GET /api/reports/1`：返回 Markdown、items 和 deliveries。
  - `POST /api/reports/1/send`：本地邮件配置可发送，返回 `status=sent`。
  - `GET /api/reports/1/markdown`：返回 200 和 Markdown 内容。
- Docker Desktop 管道在普通命令下偶发 `permission denied`，提升权限后容器内单元测试通过。

## 遇到的问题
| 问题 | 解决方案 |
|------|---------|
| 本地 Python 缺少后端依赖 | 不阻塞最终验证；用 Docker 镜像运行单元测试 |
| Docker Hub 直连 token 超时 | 使用 `127.0.0.1:18080` 代理拉取基础镜像并构建 |
| 邮件发送 465/SSL 兼容性不足 | 新增 `open_smtp_connection`，465 走 `SMTP_SSL`，其他端口走 STARTTLS |
| git worktree 创建分支失败 | `.git/refs/heads` 写入 lock 文件 permission denied，记录后继续在 main 工作树实现 |

## 资源
- 本地仓库：`C:\Users\aodo\PaperPulse`
- 远程仓库：`https://github.com/uovme/PaperPulse.git`

## 视觉/浏览器发现
-

---
*每执行2次查看/浏览器/搜索操作后更新此文件*
*防止视觉信息丢失*
