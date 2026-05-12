<div align="center">

# PaperPulse

**Smart journal paper tracker — RSS subscription, AI literature analysis, workflow progress, email reports.**

![Docker](https://img.shields.io/badge/Docker-Ready-blue?style=flat&logo=docker&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.12-green?style=flat&logo=python&logoColor=white)
![Vue](https://img.shields.io/badge/Vue-3-brightgreen?style=flat&logo=vuedotjs&logoColor=white)

[中文](#中文) | [English](#english)

</div>

---

## 中文

### 功能

- **RSS 订阅** — 添加多个学术期刊 RSS 源，自动每日抓取新论文
- **关键词匹配** — 设置研究关键词，AI 自动分析论文标题和摘要相关性
- **AI 文献汇总分析** — 支持 OpenAI / DeepSeek 等兼容 API，输出相关性评分、匹配主题词和中文摘要
- **分析结果页** — 独立查看论文标题、摘要、作者、期刊、原文链接、AI 评分和分析总结
- **阅读队列** — 手工保存外部论文/文章，支持标签、搜索、待读/已读状态和备注
- **工作流进度** — 抓取、分析、邮件、WebDAV 备份都有执行记录、节点日志和进度条
- **分析任务控制** — 长时间 AI 分析支持暂停、继续、取消；抓取并分析时总数按本次新抓取论文计算
- **邮件推送** — 高相关性论文每日自动推送到邮箱，支持 SMTP SSL/STARTTLS，邮件正文包含摘要
- **WebDAV 同步** — 数据备份到坚果云等 WebDAV 服务
- **论文分类** — 按期刊、关键词、相关性分值筛选
- **链接清洗** — 自动移除 ScienceDirect `dgcid`、`utm_*` 等 RSS 跟踪参数，保留干净原文链接
- **Web UI** — 仪表盘、订阅管理、论文浏览、关键词管理、设置

### 快速开始

#### Docker（推荐）

```bash
git clone https://github.com/uovme/PaperPulse.git
cd PaperPulse
docker compose up -d
# 访问 http://localhost:18095
```

默认端口只绑定本机：`127.0.0.1:18095 -> 8000`。如需外网访问，请在反向代理中转发到 `127.0.0.1:18095`。

常用命令：

```bash
docker compose ps
docker compose logs -f
docker compose up -d --build
```

数据默认保存在 `./data/paperpulse.db`，升级镜像不会删除历史数据。

#### 源码运行

```bash
# 后端
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# 前端
cd frontend
npm install
npm run dev
```

### 配置

在 Web UI 的设置页面配置：

1. **AI 配置** — 填入 API 地址、Key、模型名（如 DeepSeek: `https://api.deepseek.com/v1`）
2. **邮件配置** — SMTP 服务器信息
3. **WebDAV 配置** — WebDAV 地址和凭证
4. **定时任务** — 设置每日执行时间和相关性阈值

### 使用流程

1. 添加 RSS 订阅源（如 Nature: `https://www.nature.com/nature.rss`）
2. 添加研究关键词（如 "nickel alloy", "superalloy", "高温合金"）
3. 点击「一键抓取并分析」或等待每日自动执行
4. 在仪表盘查看执行进度、已分析数量、总数、主题词相关数量
5. 如分析耗时较长，可暂停、继续或取消
6. 在「分析结果」页面查看 AI 分析详情和原文链接
7. 在「阅读队列」中保存需要稍后阅读的外部论文或文章
8. 配置邮件后自动推送每日报告

### 工作流 API

主要接口：

- `POST /api/analysis/run-background` — 后台运行待分析论文汇总分析
- `POST /api/analysis/fetch-and-analyze-background` — 后台抓取并分析，本次进度总数等于新抓取论文数
- `GET /api/executions` — 查看最近工作流执行记录
- `GET /api/executions/{id}` — 查看执行详情和节点日志
- `POST /api/executions/{id}/pause` — 暂停分析
- `POST /api/executions/{id}/resume` — 继续分析
- `POST /api/executions/{id}/cancel` — 取消分析
- `GET /api/reading-queue` — 阅读队列列表，支持 `search`、`status`、`tag`、分页
- `POST /api/reading-queue` — 添加阅读队列条目
- `PUT /api/reading-queue/{id}` — 更新条目或切换待读/已读
- `DELETE /api/reading-queue/{id}` — 删除条目

说明：暂停/取消采用协作式控制，当前正在请求中的单篇 AI 分析会先完成，然后再暂停或取消后续论文。

---

## English

### Features

- **RSS Subscriptions** — Add multiple journal RSS feeds, auto-fetch daily
- **Keyword Matching** — Set research keywords, AI analyzes title and abstract relevance
- **AI Literature Analysis** — Supports OpenAI / DeepSeek compatible APIs with scores, matched keywords, and Chinese summaries
- **Analysis Results Page** — Review paper titles, abstracts, authors, journals, source links, AI scores, and summaries
- **Reading Queue** — Manually save external papers or articles with tags, search, unread/read status, and notes
- **Observable Workflows** — Fetch, analyze, email, and WebDAV backup steps are persisted with execution logs and progress
- **Analysis Controls** — Long-running AI analysis can be paused, resumed, or cancelled
- **Email Push** — Daily auto-push of highly relevant papers with abstract content; supports SMTP SSL/STARTTLS
- **WebDAV Sync** — Backup data to WebDAV services
- **Paper Classification** — Filter by journal, keyword, relevance score
- **Clean Source Links** — Removes RSS tracking parameters such as ScienceDirect `dgcid` and `utm_*`
- **Web UI** — Dashboard, feed management, paper browser, keyword management, settings

### Quick Start

```bash
git clone https://github.com/uovme/PaperPulse.git
cd PaperPulse
docker compose up -d
# Open http://localhost:18095
```

The default compose file binds only to localhost: `127.0.0.1:18095 -> 8000`. Use a reverse proxy for public access.

Useful commands:

```bash
docker compose ps
docker compose logs -f
docker compose up -d --build
```

Application data is stored in `./data/paperpulse.db`.

### Workflow

1. Add RSS feeds (e.g., Nature: `https://www.nature.com/nature.rss`)
2. Add keywords (e.g., "nickel alloy", "superalloy", "precipitation hardening")
3. Click "Fetch & Analyze" or wait for daily auto-run
4. Track progress on the dashboard: analyzed count, total count, and keyword-related count
5. Pause, resume, or cancel long-running analysis jobs when needed
6. Review detailed AI results on the Analysis page
7. Save external papers or articles to the Reading Queue for later
8. Configure email for automatic daily reports

### Workflow API

- `POST /api/analysis/run-background` — Run background analysis for pending papers
- `POST /api/analysis/fetch-and-analyze-background` — Fetch and analyze in the background; total count equals newly fetched papers
- `GET /api/executions` — List workflow executions
- `GET /api/executions/{id}` — Get execution detail and node logs
- `POST /api/executions/{id}/pause` — Pause analysis
- `POST /api/executions/{id}/resume` — Resume analysis
- `POST /api/executions/{id}/cancel` — Cancel analysis
- `GET /api/reading-queue` — List reading queue items with `search`, `status`, `tag`, and pagination
- `POST /api/reading-queue` — Create a reading queue item
- `PUT /api/reading-queue/{id}` — Update an item or toggle unread/read status
- `DELETE /api/reading-queue/{id}` — Delete an item

## License

MIT
