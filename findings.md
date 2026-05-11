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

## 遇到的问题
| 问题 | 解决方案 |
|------|---------|
| 本地 Python 缺少后端依赖 | 不阻塞最终验证；用 Docker 镜像运行单元测试 |
| Docker Hub 直连 token 超时 | 使用 `127.0.0.1:18080` 代理拉取基础镜像并构建 |
| 邮件发送 465/SSL 兼容性不足 | 新增 `open_smtp_connection`，465 走 `SMTP_SSL`，其他端口走 STARTTLS |

## 资源
- 本地仓库：`C:\Users\aodo\PaperPulse`
- 远程仓库：`https://github.com/uovme/PaperPulse.git`

## 视觉/浏览器发现
-

---
*每执行2次查看/浏览器/搜索操作后更新此文件*
*防止视觉信息丢失*
