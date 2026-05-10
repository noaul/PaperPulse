<div align="center">

# PaperPulse

**Smart journal paper tracker — RSS subscription, AI analysis, email push.**

![Docker](https://img.shields.io/badge/Docker-Ready-blue?style=flat&logo=docker&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.12-green?style=flat&logo=python&logoColor=white)
![Vue](https://img.shields.io/badge/Vue-3-brightgreen?style=flat&logo=vuedotjs&logoColor=white)

[中文](#中文) | [English](#english)

</div>

---

## 中文

### 功能

- **RSS 订阅** — 添加多个学术期刊 RSS 源，自动每日抓取新论文
- **关键词匹配** — 设置研究关键词，AI 自动分析论文摘要相关性
- **AI 分析** — 支持 OpenAI / DeepSeek 等兼容 API，评分+中文摘要
- **邮件推送** — 高相关性论文每日自动推送到邮箱
- **WebDAV 同步** — 数据备份到坚果云等 WebDAV 服务
- **论文分类** — 按期刊、关键词、相关性分值筛选
- **Web UI** — 仪表盘、订阅管理、论文浏览、关键词管理、设置

### 快速开始

#### Docker（推荐）

```bash
git clone https://github.com/uovme/PaperPulse.git
cd PaperPulse
docker compose up -d
# 访问 http://localhost:18095
```

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
3. 点击「抓取并分析」或等待每日自动执行
4. 查看分析结果，高相关性论文会高亮显示
5. 配置邮件后自动推送每日报告

---

## English

### Features

- **RSS Subscriptions** — Add multiple journal RSS feeds, auto-fetch daily
- **Keyword Matching** — Set research keywords, AI analyzes abstract relevance
- **AI Analysis** — Supports OpenAI / DeepSeek compatible APIs with scoring + summaries
- **Email Push** — Daily auto-push of highly relevant papers to your inbox
- **WebDAV Sync** — Backup data to WebDAV services
- **Paper Classification** — Filter by journal, keyword, relevance score
- **Web UI** — Dashboard, feed management, paper browser, keyword management, settings

### Quick Start

```bash
git clone https://github.com/uovme/PaperPulse.git
cd PaperPulse
docker compose up -d
# Open http://localhost:18095
```

### Workflow

1. Add RSS feeds (e.g., Nature: `https://www.nature.com/nature.rss`)
2. Add keywords (e.g., "nickel alloy", "superalloy", "precipitation hardening")
3. Click "Fetch & Analyze" or wait for daily auto-run
4. Review analysis results with relevance scores
5. Configure email for automatic daily reports

## License

MIT
