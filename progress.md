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
