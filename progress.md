# 进度日志

## 会话：2026-05-11

### 阶段 13：全面升级规划与第一批实施范围
- **状态：** in_progress
- 用户请求：
  - “现在开始这个项目，这个项目需要全面升级”
- 已执行：
  - 使用 `brainstorm` 做需求发现和路线拆分。
  - 使用 `planning-with-files-zh` 恢复并维护 `task_plan.md/findings.md/progress.md`。
  - 确认本地仓库 `C:\Users\aodo\PaperPulse` 已存在，远端 `git pull --ff-only` 后已是最新。
  - 读取 README、Dockerfile、docker-compose、前后端依赖、后端模型/API、前端路由/API。
  - 确认当前代码已有 workflow engine、执行记录、分析结果页、暂停/继续/取消和 nc48 部署记录。
  - 将阶段 13 写入计划文件，并补充全面升级候选路线图。
- 当前判断：
  - 不建议直接无边界重写；应按 P0/P1/P2/P3 分批升级。
  - 第一批最稳的升级是“报告中心 + 邮件投递记录 + 数据库迁移基础”，因为它延续现有分析/邮件/workflow 闭环。
- 待用户确认：
  - 是否按推荐 P0 批次开始实现。
  - 是否允许先创建 git worktree 隔离实现分支。

### 阶段 14：P0 报告中心与邮件投递记录
- **状态：** in_progress
- 已执行：
  - 新增 `Report`、`ReportItem`、`EmailDelivery` 模型，用数据库持久化报告内容和每次邮件投递状态。
  - 新增 `backend/app/services/report_center.py`，封装今日高相关分析结果收集、报告生成、Markdown 渲染、邮件发送和投递记录。
  - `send_daily_report()` 改为委托报告中心服务，旧邮件入口保持兼容，同时每日邮件会生成可追踪报告。
  - 新增 `/api/reports` API：列表、创建、详情、发送、Markdown 下载、投递记录。
  - 新增前端“报告中心”页面和侧边栏入口，支持生成报告、查看条目、Markdown 预览/下载、发送邮件和查看投递记录。
  - 新增 `backend/tests/test_reports.py` 覆盖报告持久化、去重、邮件跳过和发送成功记录。
- 验证：
  - `python -m compileall backend\app`：通过。
  - `npm run build`：通过，生成 `Reports` 前端 chunk。
  - `docker run --rm -v ${PWD}\backend:/src:ro -w /src paperpulse-app python -m unittest tests.test_reports tests.test_email_sender tests.test_rss_fetcher tests.test_workflow_engine`：18 tests OK。
  - `docker compose up -d --build`：通过，容器 healthy。
  - `GET /api/health`：200，返回 `{"status":"ok","version":"1.0.0"}`。
  - `GET /reports`：200。
  - `POST /api/reports`：认证后生成报告 `id=1`，31 条报告项。
  - `GET /api/reports/1`：返回详情、Markdown、items。
  - `POST /api/reports/1/send`：返回 `status=sent`。
  - `GET /api/reports/1/markdown`：200，返回 Markdown。
  - GitHub：已推送 `66a9947 feat: add persistent report center` 到 `origin/main`。
  - nc48：`/opt/PaperPulse` 已拉取 `66a9947`，`docker compose up -d --build` 完成。
  - nc48：容器 `paperpulse` healthy，端口 `127.0.0.1:18095->8000`。
  - nc48：`GET /api/health` 返回 `{"status":"ok","version":"1.0.0"}`。
  - nc48：`GET /reports` 返回 200。
  - nc48：容器内 SQLite 已确认存在 `reports`、`report_items`、`email_deliveries` 表。
- 遇到的问题：
  - `git worktree` 创建隔离分支失败：`.git/refs/heads/upgrade-reports.lock` permission denied；已记录并继续在 main 工作树实现。
  - 普通权限下 Docker Desktop 管道偶发 permission denied；提升权限后测试通过。
  - nc48 首次部署后立即 curl 时容器仍在 `health: starting`，出现 connection reset；等待 healthy 后复测通过。
  - nc48 主机无 `sqlite3` CLI；改用容器内 Python 检查数据库表结构。

### 阶段 15：前端视觉重构
- **状态：** in_progress
- 用户反馈：
  - “重构一下前端吧，现在的不好看”
- 已执行：
  - 重写 `frontend/src/style.css` 全局视觉系统：浅色研究工作台背景、玻璃质感卡片、统一按钮/输入/滚动条、全局阴影和边框。
  - 重构 `App.vue`：侧边栏改为浅色半透明导航，顶部栏增加副标题和在线状态。
  - 重构 `Login.vue`：登录页改成同一视觉语言的居中工作台入口。
  - 优化 `Dashboard.vue` 统计卡和快速操作层次。
  - 优化 `Reports.vue` 顶部报告生成区域和详情面板高度。
  - 优化 `Papers.vue` 标题层级。
- 验证：
  - `npm run build`：通过。
  - `docker compose up -d --build`：本地构建启动通过，容器 healthy。
  - `GET /api/health`：200。
  - `GET /login`、`/dashboard`、`/reports`、`/papers`、`/settings`：均返回 200。
  - GitHub：已推送 `aa24641 feat: refresh frontend visual design` 到 `origin/main`。
  - nc48：`/opt/PaperPulse` 已拉取 `aa24641`，`docker compose up -d --build` 完成。
  - nc48：容器 healthy，`GET /api/health` 返回 OK。
  - nc48：`/login`、`/dashboard`、`/reports`、`/papers`、`/settings` 均返回 200。

### 阶段 1：基线确认与重构边界
- **状态：** complete
- **开始时间：** 2026-05-11
- 执行的操作：
  - 读取规划技能。
  - 确认本地无规划文件。
  - 检查 Git 状态，当前 `main...origin/main` 且工作区干净。
  - 创建本次重构规划文件。
  - 梳理后端模型、服务、路由、数据库初始化方式。
  - 梳理前端 API 和 Dashboard 页面作为执行状态展示入口。
- 创建/修改的文件：
  - `task_plan.md`
  - `findings.md`
  - `progress.md`

### 阶段 2：后端轻量工作流内核
- **状态：** complete
- 执行的操作：
  - 新增 `WorkflowExecution` / `WorkflowExecutionLog` 模型。
  - 新增 workflow engine、context、node 抽象。
  - 新增 fetch-rss、ai-analyze、email-report、webdav-backup 节点。
  - 将手动分析、抓取分析、发送报告和每日任务接入 workflow。
- 创建/修改的文件：
  - `backend/app/models.py`
  - `backend/app/workflows/**`
  - `backend/app/routers/analysis.py`
  - `backend/app/main.py`

### 阶段 3：执行记录 API
- **状态：** complete
- 执行的操作：
  - 新增执行记录列表、详情、日志 API。
  - 新增每日完整工作流手动运行 API。
- 创建/修改的文件：
  - `backend/app/routers/executions.py`
  - `backend/app/routers/workflows.py`
  - `backend/app/schemas.py`

### 阶段 4：前端保留现有使用方式并增强
- **状态：** complete
- 执行的操作：
  - 扩展前端 API 类型与 execution/workflow 调用。
  - Dashboard 增加工作流执行记录列表与节点日志详情。
  - 快速操作新增“运行完整工作流”。
- 创建/修改的文件：
  - `frontend/src/api/index.ts`
  - `frontend/src/views/Dashboard.vue`

### 阶段 7：修复长时间 AI 分析超时并增加进度
- **状态：** complete
- 用户反馈：
  - Dashboard 点击“运行分析”报错：`timeout of 30000ms exceeded`
  - 需要文献汇总分析进度条：已分析多少、总共多少、和主题词相关的多少。
- 初步根因：
  - 当前 `/api/analysis/run` 在单个 HTTP 请求里同步跑批量 AI 分析。
  - 前端 axios 全局 timeout 为 30000ms。
  - 抓取后已有较多论文时，AI 分析必然超过 30 秒，导致前端超时。
  - 后端日志还显示 AI 配置为空/未启用时只记录日志，前端提示不够明确。
- 已执行：
  - 新增 `WorkflowContext.update_summary()`，支持长任务运行中持续写入 summary。
  - `/api/analysis/run-background` 与 `/api/analysis/fetch-and-analyze-background` 改为立即返回 execution_id，后台继续执行。
  - AI 分析服务增加 `analysis_total`、`analysis_analyzed`、`analysis_related`、`analysis_results`、`analysis_current_title`、`literature_summary` 进度字段。
  - Dashboard 增加“文献汇总分析进度”进度条和三项计数。
  - Dashboard 的运行分析/抓取并分析按钮改用后台接口并轮询 execution。

### 阶段 8：分析结果页面与邮件发送修复
- **状态：** complete
- 用户反馈：
  - 需要一个能直接看到 AI 分析结果的页面。
  - 邮件发送功能有问题。
- 初步判断：
  - 当前已有 `/api/analysis`，但前端类型定义按分页对象使用，后端实际返回 list，适合作为本阶段修复点。
  - 邮件服务对 SMTP 465/SSL 不兼容，且论文 URL 生成表达式有优先级问题；邮件发送结果也缺少明确原因。
- 已执行：
  - 新增前端 `/analysis` 页面和侧边栏入口，用于查看 AI 分析结果。
  - `/api/analysis` 改为分页响应，并返回论文标题、摘要、作者、原文链接、期刊和主题词。
  - RSS 抓取新增 HTML 清洗和更稳的摘要提取，支持 `summary`、`description`、`content` 等字段。
  - 论文列表和分析结果 API 对旧数据中的 HTML 标记做输出清洗。
  - 邮件发送支持 465 端口 SMTP_SSL；587/其他端口仍走 STARTTLS。
  - 邮件报告包含论文摘要；发送结果返回 skipped/reason/paper_count，前端显示具体原因。

### 阶段 9：后续功能规划与复杂度分析
- **状态：** complete
- 执行的操作：
  - 梳理后续可增加功能。
  - 按用户价值、复杂度、主要改动和风险做矩阵。
  - 建议下一轮优先做“报告中心 + 邮件预览/重发 + 摘要增强”。
- 创建/修改的文件：
  - `task_plan.md`
  - `findings.md`
  - `progress.md`

## 测试结果
| 测试 | 输入 | 预期结果 | 实际结果 | 状态 |
|------|------|---------|---------|------|
| `python -m unittest backend.tests.test_workflow_engine` | 新增 workflow engine 行为测试 | 先失败，证明功能未实现 | 本地 Python 缺少 `sqlalchemy`，测试环境不可用 | blocked-local-env |
| `python -m compileall backend\app` | 后端应用代码 | 语法编译通过 | 编译通过 | pass |
| `npm run build` | frontend | 前端生产构建通过 | 构建通过，生成 `backend/static` 资源 | pass |
| `docker compose up -d --build` | 本地 Docker | 构建并启动健康容器 | 初次直连 Docker Hub 失败，改走 `127.0.0.1:18080` 代理后成功 | pass |
| `GET /api/health` | 本地容器 `127.0.0.1:18095` | 200 + ok | 200 + ok | pass |
| `GET /dashboard`, `/login`, `/papers` | 本地容器 SPA 路由 | 200 | 200 | pass |
| `POST /api/workflows/daily/run` | 本地容器 | 生成 workflow execution | success，生成执行记录和节点日志 | pass |
| `POST /api/analysis/fetch-and-analyze` | 本地容器 | 保持旧接口字段并生成 execution | success，返回 `new_papers`/`analyses`/`execution_id` | pass |
| `POST /api/analysis/run` | 本地容器 | 保持旧接口字段并生成 execution | success，返回 `analyzed`/`execution_id` | pass |
| `POST /api/analysis/send-report` | 本地容器 | 保持旧接口字段并生成 execution | success=false（未配置邮箱），执行记录 status=success | pass |
| `docker run ... python -m unittest tests.test_workflow_engine` | 容器内后端单元测试 | 2 个 workflow engine 测试通过 | OK | pass |
| `docker run ... python -m unittest tests.test_workflow_engine` | 新增进度持久化测试 | 3 个 workflow engine 测试通过 | OK | pass |
| `POST /api/analysis/run-background` | 本地容器，带登录 token | 10 秒内返回 execution_id，不触发 30 秒超时 | 2.9 秒返回 `execution_id=18`, status=running | pass |
| `GET /api/executions/18` | 本地容器，带登录 token | 进度字段持续更新 | 已看到 `analysis_total=50`, `analysis_analyzed=9`, `analysis_related=0` | pass |
| `docker run ... unittest tests.test_email_sender tests.test_rss_fetcher tests.test_workflow_engine` | 容器内单元测试 | 邮件、RSS 摘要、workflow 测试通过 | 8 tests OK | pass |
| `GET /analysis` | 本地容器 SPA 路由 | 200 | 200 | pass |
| `GET /api/analysis?page=1&page_size=1` | 本地容器，带登录 token | 分页返回并包含摘要字段 | 返回 `items/total/page/pages`，摘要已清理 HTML | pass |

## 错误日志
| 时间戳 | 错误 | 尝试次数 | 解决方案 |
|--------|------|---------|---------|
| 2026-05-11 | 本地 Python 运行 unittest 缺少后端依赖 `sqlalchemy` | 1 | 记录为环境问题，后续使用 Docker 构建环境验证；如需要可再安装本地依赖 |
| 2026-05-11 | Docker 直连 Docker Hub 拉取 `python:3.12-slim` token 超时 | 2 | 使用本机 `127.0.0.1:18080` 代理先 `docker pull python:3.12-slim`，再构建成功 |
| 2026-05-11 | 用户反馈 `http://127.0.0.1:18095` 访问不了 | 1 | 已检查容器 healthy、端口测试成功、PowerShell 访问 `/` 与 `/api/health` 均 200；可能是用户访问时容器正重建/重启或浏览器代理问题 |
| 2026-05-11 | 运行分析报 `timeout of 30000ms exceeded` | 1 | 改为后台执行 + 前端轮询进度，而不是延长超时时间 |
| 2026-05-11 | ScienceDirect 原文链接保留 `?dgcid=rss_sd_all` 等 RSS 跟踪参数 | 1 | 新增 `normalize_paper_url()`，抓取入库、论文 API、分析 API、邮件链接统一清洗跟踪参数 |

### 链接清洗修复与验证
- 新增回归测试：ScienceDirect `?dgcid=rss_sd_all` 会被移除，普通业务查询参数会保留。
- 修改位置：
  - `backend/app/services/rss_fetcher.py`
  - `backend/app/services/email_sender.py`
  - `backend/app/routers/papers.py`
  - `backend/app/routers/analysis.py`
  - `backend/tests/test_rss_fetcher.py`
- 验证结果：
  - `docker run --rm -v ${PWD}\backend:/src:ro -w /src paperpulse-app python -m unittest tests.test_email_sender tests.test_rss_fetcher tests.test_workflow_engine`：10 tests OK
  - `python -m compileall backend\app`：通过
  - `npm run build`：通过
  - `docker compose up -d --build`：通过，容器 healthy
  - 容器内函数验证：`https://www.sciencedirect.com/science/article/pii/S1359645426004003?dgcid=rss_sd_all` 输出为无查询参数的原文链接

### 进度总数与分析控制
- 用户要求：
  - 文献汇总分析进度中的“文献总数”应为本次新抓取文章总数。
  - 增加文献分析暂停和取消功能。
- 已执行：
  - `FetchRssNode` 将本次新抓取论文 ID 写入 workflow `state.fetched_paper_ids`。
  - `AiAnalyzeNode` 将这些 ID 传给 `analyze_new_papers()`，抓取并分析时只分析本次新抓取论文，进度总数等于新抓取论文数。
  - `WorkflowContext` 新增协作式控制：`pause_requested` / `paused` / `running` / `cancel_requested` / `cancelled`。
  - `POST /api/executions/{id}/pause`、`resume`、`cancel` 已实现。
  - Dashboard 进度卡片增加暂停、继续、取消按钮；暂停/取消状态会继续轮询或显示终态。
- 验证结果：
  - `docker run --rm -v ${PWD}\backend:/src:ro -w /src paperpulse-app python -m unittest tests.test_workflow_engine`：8 tests OK
  - `docker run --rm -v ${PWD}\backend:/src:ro -w /src paperpulse-app python -m unittest tests.test_email_sender tests.test_rss_fetcher tests.test_workflow_engine`：15 tests OK
  - `python -m compileall backend\app`：通过
  - `npm run build`：通过
  - `docker compose up -d --build`：通过，容器 healthy
  - `GET /api/health`：200
  - `GET /dashboard`：200
- Git:
  - 已提交：`c4a159b feat: add observable analysis workflow controls`
  - 已推送：`origin/main`

### README 更新与 nc48 部署
- README 已更新：
  - 新增工作流进度、分析结果页、暂停/继续/取消、链接清洗、Workflow API、Docker 端口和数据说明。
- Git:
  - 已提交：`543b20e docs: update workflow documentation`
  - 已推送：`origin/main`
- nc48:
  - 项目目录：`/opt/PaperPulse`
  - 已执行 `git pull --ff-only`
  - 已执行 `docker compose up -d --build`
  - 当前提交：`543b20e`
  - 容器：`paperpulse` healthy，端口 `127.0.0.1:18095->8000`
  - 验证：
    - `/api/health` 返回 `{"status":"ok","version":"1.0.0"}`
    - `/`、`/login`、`/dashboard`、`/analysis`、`/papers`、`/settings` 均返回 200

### Credit 风格暗色前端调整
- 用户偏好参考：`https://github.com/linux-do/credit` / `https://credit.linux.do/`
- 已执行：
  - 将 PaperPulse 全局主题从浅色研究工作台调整为暗色开发者仪表盘风格。
  - 采用 OKLCH 暗色 token、半透明卡片、低对比边框、紧凑圆角、蓝/绿/紫少量强调色和 tabular 数字风格。
  - 补齐旧 Tailwind 浅色类在暗色主题下的覆盖：卡片、表格、徽章、状态提示、弹窗、分页、hover、toast、加载动画。
  - 保持页面结构和业务逻辑不变，只调整全局视觉系统和构建产物。
- 修改位置：
  - `frontend/src/style.css`
  - `backend/static`
- 验证结果：
  - `npm run build`：通过
  - `docker compose up -d --build`：通过，容器 healthy
  - `GET /api/health`：200，返回 `{"status":"ok","version":"1.0.0"}`
  - `GET /login`、`/dashboard`、`/reports`、`/papers`、`/settings`：均 200
- Git:
  - 已提交：`49dfcb7 feat: align frontend with credit dashboard style`
  - 已推送：`origin/main`
- nc48:
  - `/opt/PaperPulse` 已 fast-forward 到 `49dfcb7`
  - 已执行 `docker compose up -d --build`
  - 容器 `paperpulse` healthy，端口 `127.0.0.1:18095->8000`
  - 验证 `/api/health`、`/login`、`/dashboard`、`/reports`、`/papers`、`/settings` 均通过

### 移除默认文献分析 50 篇上限
- 用户问题：
  - “文献分析总数上限是50吗，能不能调成新获取文献的所有数量”
- 定位：
  - RSS 抓取没有 50 限制。
  - `fetch-and-analyze` 路径已通过 `fetched_paper_ids` 限定为本次新抓取论文，理论上会分析本次新获取的全部论文。
  - 单独运行“分析已有未分析论文”路径在 `analyze_new_papers()` 未传 `paper_ids` 时存在 `.limit(50)`。
- 已执行：
  - 新增 55 篇待分析论文回归测试，先确认当前只分析 50 篇。
  - 移除 `backend/app/services/ai_analyzer.py` 中默认查询的 `.limit(50)`。
  - 保留传入 `paper_ids` 时的行为：抓取并分析只处理本次新抓取论文全集。
- 验证结果：
  - 新增测试先失败：`AssertionError: 55 != 50`
  - 修复后关键 3 个 workflow 测试通过
  - `docker run ... python -m unittest tests.test_ai_analyzer tests.test_reports tests.test_email_sender tests.test_rss_fetcher tests.test_workflow_engine`：23 tests OK
  - `python -m compileall backend\app`：通过
  - `npm run build`：通过
  - 本地 `docker compose up -d --build`：容器 healthy
  - 本地 `/api/health`、`/login`、`/dashboard`、`/reports`、`/papers`、`/settings`：通过
- Git:
  - 已提交：`ed05634 fix: analyze all pending papers`
  - 已推送：`origin/main`
- nc48:
  - `/opt/PaperPulse` 已 fast-forward 到 `ed05634`
  - 已执行 `docker compose up -d --build`
  - 容器 `paperpulse` healthy，端口 `127.0.0.1:18095->8000`
  - 验证 `/api/health`、`/login`、`/dashboard`、`/reports`、`/papers`、`/settings` 均通过

## 五问重启检查
| 问题 | 答案 |
|------|------|
| 我在哪里？ | 阶段 9：后续功能规划与复杂度分析 |
| 我要去哪里？ | 实现 workflow/execution/log 重构并本地 Docker 验证 |
| 目标是什么？ | 保持功能兼容，提升 PaperPulse 架构工程化程度 |
| 我学到了什么？ | 见 findings.md |
| 我做了什么？ | 见上方记录 |

---
*每个阶段完成后或遇到错误时更新此文件*

## 2026-05-12：阶段 18 阅读队列功能移植
- 用户要求：把 PaperTrail 练习项目里的阅读队列功能添加到 `https://github.com/uovme/PaperPulse`，测试后推送。
- 当前仓库：`C:\Users\aodo\PaperPulse`，分支 `main...origin/main`，远端 `https://github.com/uovme/PaperPulse.git`。
- 初始工作区已有未提交变更：`task_plan.md`、`progress.md`，本轮不回滚，继续维护规划文件。
- 实现边界：把阅读队列作为独立轻量工具接入 PaperPulse，用于手工保存论文/文章；不改现有 RSS Paper 自动抓取模型和分析 workflow。
- 下一步：先写后端阅读队列 CRUD/筛选测试，确认失败后实现模型、schema、router。
- TDD 红灯：新增 `backend/tests/test_reading_queue.py` 后，`POST /api/reading-queue` 返回 405，确认功能缺失。
- 后端实现：
  - 新增 `ReadingQueueItem` 模型，支持 `tags_json`、`status`、`notes`、创建/更新时间。
  - 新增阅读队列 schema：创建、更新、输出、分页列表。
  - 新增 `/api/reading-queue` CRUD API，支持搜索、状态筛选、标签筛选和分页。
  - `main.py` 注册 reading queue router。
- 后端测试绿灯：`docker run --rm -v ${PWD}\backend:/src:ro -w /src paperpulse-app python -m unittest tests.test_reading_queue`，3 tests OK。
- 前端实现：
  - `frontend/src/api/index.ts` 新增 readingQueueApi 和类型。
  - `frontend/src/router/index.ts` 新增 `/reading-queue`。
  - `frontend/src/App.vue` 侧边栏新增“阅读队列”。
  - 新增 `frontend/src/views/ReadingQueue.vue`，支持列表、搜索、状态/标签筛选、添加、编辑、删除、待读/已读切换。
- README 已补充阅读队列功能、使用流程和 API。
- 验证结果：
  - `python -m compileall backend\app`：通过。
  - `npm run build`：通过，生成 `ReadingQueue-ghrLGspl.js`。
  - `docker run --rm -v ${PWD}\backend:/src:ro -w /src paperpulse-app python -m unittest tests.test_reading_queue tests.test_reports tests.test_email_sender tests.test_rss_fetcher tests.test_workflow_engine`：22 tests OK。
  - `docker compose up -d --build`：通过，容器 `paperpulse` healthy。
  - `GET http://localhost:18095/api/health`：200。
  - `GET http://localhost:18095/reading-queue`：200。
  - 静态资源 `/assets/ReadingQueue-ghrLGspl.js` 和 `/assets/index-DQTAS3MD.css`：200。
  - 未登录访问 `/api/reading-queue` 返回 401，符合现有认证中间件预期。
  - 使用本地 auth token 端到端验证阅读队列 API：创建、未读+标签筛选、更新已读、已读+标签筛选、删除、删除后确认均通过。
- Git:
  - 已提交：`7d9d7e6 feat: add reading queue`。

### 阶段 18 nc48 重新部署
- 用户要求：在 nc48 上重新部署 PaperPulse。
- nc48 项目目录：`/opt/PaperPulse`。
- 已执行：`git pull --ff-only`，从 `4baeeac` fast-forward 到 `33be432`。
- 已执行：`docker compose up -d --build`，镜像重新构建，容器 `paperpulse` 重新创建并启动。
- 验证结果：
  - 当前提交：`33be432`。
  - 容器状态：`paperpulse` healthy，端口 `127.0.0.1:18095->8000`。
  - `GET /api/health` 返回 `{"status":"ok","version":"1.0.0"}`。
  - `/`、`/login`、`/dashboard`、`/reports`、`/papers`、`/reading-queue`、`/settings` 均返回 200。
  - `/assets/ReadingQueue-ghrLGspl.js` 返回 200。
  - 未登录访问 `/api/reading-queue` 返回 401，符合认证保护预期。

## 2026-05-12：阶段 19 批量管理、最新抓取分析与持久化
- 用户要求：
  - 运行分析只分析抓取的最新文献和未分析的文献。
  - 订阅源添加全部刷新和批量删除功能。
  - 论文分析结果可直接添加到阅读队列。
  - 关键词可批量添加。
  - 修改完成后推送并在 nc48 上重新部署。
  - AI 分析结果保存不能每次重新部署就没了。
- 根因判断：
  - 当前 `docker-compose.yml` 已将 `./data` 挂载到 `/app/data`，`DB_PATH=/app/data/paperpulse.db`，正常 `docker compose up -d --build` 不应删除 AI 分析结果。
  - 现有 WebDAV 备份只导出 feeds/keywords，不包含 papers/analysis_results，换机或数据目录误删时无法恢复 AI 分析结果。
  - `fetch-and-analyze` 已传递本次抓取 `paper_ids`，但手动 `run-analysis` 未传目标，会扫描全部未分析论文。
- 红灯测试：
  - `tests.test_bulk_features` 新增订阅源全部刷新、批量删除、关键词批量添加、分析结果入阅读队列测试。
  - `tests.test_webdav_sync` 新增 WebDAV 导出包含 papers/analysis_results 测试。
  - `tests.test_workflow_engine.WorkflowEngineTest.test_analyze_new_papers_without_targets_uses_latest_fetch_batch_only` 修改为验证手动分析使用最新抓取批次。
  - 红灯结果：批量 API 和入队 API 返回 405；WebDAV 导出缺少 `papers`；手动分析分析了旧待分析论文。
- 已实现：
  - `latest_fetched_paper_ids` 持久化到 `settings`；单源抓取、全部刷新和 workflow 抓取都会更新最新抓取批次。
  - `analyze_new_papers()` 未显式传 `paper_ids` 时优先读取最新抓取批次，只分析该批次里尚未分析的论文；老库没有批次记录时保持原有未分析论文兜底逻辑。
  - 新增 `/api/feeds/fetch-all`、`/api/feeds/bulk-delete`、`/api/keywords/bulk`、`/api/analysis/{id}/add-to-reading-queue`。
  - WebDAV 导出/导入扩展到 papers 和 analysis_results。
  - 前端 Feeds 页新增全部刷新、勾选和批量删除；Keywords 页新增批量添加；Analysis 页新增加入阅读队列按钮。
  - README 补充新增接口、最新抓取分析口径和数据持久化说明。
- 验证：
  - 红灯集修复后：`docker run ... python -m unittest tests.test_bulk_features tests.test_webdav_sync tests.test_workflow_engine.WorkflowEngineTest.test_analyze_new_papers_without_targets_uses_latest_fetch_batch_only`：6 tests OK。
  - 回归：`docker run ... python -m unittest tests.test_bulk_features tests.test_webdav_sync tests.test_reading_queue tests.test_ai_analyzer tests.test_reports tests.test_email_sender tests.test_rss_fetcher tests.test_workflow_engine`：31 tests OK。
  - `python -m compileall backend\app`：通过。
  - `npm run build`：通过，生成新前端静态资源。
  - `docker compose up -d --build`：本地容器 `paperpulse` healthy。
  - 本地 `/api/health` 返回 OK；`/`、`/login`、`/dashboard`、`/feeds`、`/keywords`、`/analysis`、`/reading-queue`、`/settings` 均返回 200。
- Git:
  - 已提交：`db8fa3c feat: add batch management and persistent analysis flow`。
  - 已推送：`origin/main`。
- nc48 部署：
  - 部署前当前提交 `33be432`，`analysis_results` 数量 24。
  - `/opt/PaperPulse` 已 fast-forward 到 `db8fa3c`。
  - 已执行 `docker compose up -d --build`，容器 `paperpulse` healthy。
  - 部署后 `analysis_results` 数量仍为 24，论文数量 379，确认重建未清空 AI 分析结果。
  - `/api/health` 返回 OK。
  - `/`、`/login`、`/dashboard`、`/feeds`、`/keywords`、`/analysis`、`/reading-queue`、`/settings` 均返回 200。
  - 新构建资源 `/assets/Feeds-CgYkYEKN.js`、`/assets/Keywords-frsjMjOC.js`、`/assets/Analysis-CEU_-bNo.js`、`/assets/index-BmVXD3dP.css` 均返回 200。
  - 未登录访问 `/api/feeds/fetch-all` 返回 401，认证保护正常。
