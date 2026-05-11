import smtplib
import json
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import Setting, AnalysisResult, Paper, Keyword
from .rss_fetcher import clean_text, normalize_paper_url
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


async def get_email_config(db: AsyncSession) -> dict:
    result = await db.execute(select(Setting).where(Setting.key == "email_config"))
    row = result.scalar_one_or_none()
    if row:
        return json.loads(row.value)
    return {}


def build_paper_url(url: str | None, doi: str | None) -> str:
    if url:
        return normalize_paper_url(url)
    if doi:
        return f"https://doi.org/{doi}"
    return ""


def open_smtp_connection(config: dict):
    server = config["smtp_server"]
    port = int(config.get("smtp_port", 587))
    if port == 465:
        return smtplib.SMTP_SSL(server, port, timeout=20)
    return smtplib.SMTP(server, port, timeout=20)


async def build_email_html(papers_data: list[dict]) -> str:
    html = """<html><head><style>
    body{font-family:Arial,sans-serif;max-width:800px;margin:0 auto;padding:20px;color:#333}
    .paper{border:1px solid #e0e0e0;border-radius:8px;padding:16px;margin:12px 0;background:#fafafa}
    .title{font-size:16px;font-weight:bold;color:#1a5276;margin-bottom:6px}
    .title a{color:#1a5276;text-decoration:none}
    .meta{font-size:13px;color:#666;margin-bottom:8px}
    .score{display:inline-block;background:#27ae60;color:white;padding:2px 8px;border-radius:4px;font-size:12px;font-weight:bold}
    .score.mid{background:#f39c12}
    .score.low{background:#e74c3c}
    .summary{font-size:14px;color:#555;margin-top:6px;padding:8px;background:#eaf2f8;border-radius:4px}
    .abstract{font-size:13px;color:#555;margin-top:8px;line-height:1.5}
    .keyword-tag{display:inline-block;background:#3498db;color:white;padding:1px 6px;border-radius:3px;font-size:11px;margin:2px}
    h2{color:#2c3e50;border-bottom:2px solid #3498db;padding-bottom:6px}
    </style></head><body>
    <h2>📄 PaperPulse Daily Report</h2>
    <p style="color:#666">""" + datetime.now().strftime("%Y-%m-%d") + """</p>
    """

    for item in papers_data:
        score = item.get("score", 0)
        score_class = "" if score >= 7 else "mid" if score >= 5 else "low"
        html += f"""
        <div class="paper">
            <div class="title"><a href="{item.get('url', '#')}">{item['title']}</a></div>
            <div class="meta">{item.get('authors', '')} | {item.get('journal', '')} | <span class="score {score_class}">Score: {score:.1f}</span></div>
            <div>{' '.join(f'<span class="keyword-tag">{k}</span>' for k in item.get('keywords', []))}</div>
            <div class="summary">{item.get('summary', '')}</div>
            <div class="abstract"><strong>Abstract:</strong> {item.get('abstract', '')}</div>
        </div>"""

    html += "</body></html>"
    return html


async def send_daily_report(db: AsyncSession, threshold: float = 6.0) -> dict:
    config = await get_email_config(db)
    if not config.get("enabled") or not config.get("recipient"):
        message = "邮件未启用或收件人为空"
        logger.info(message)
        return {"sent": False, "skipped": True, "reason": message, "paper_count": 0}

    # Get today's high-relevance analyses
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(AnalysisResult, Paper, Keyword)
        .join(Paper, AnalysisResult.paper_id == Paper.id)
        .join(Keyword, AnalysisResult.keyword_id == Keyword.id)
        .where(AnalysisResult.analyzed_at >= today)
        .where(AnalysisResult.relevance_score >= threshold)
        .order_by(AnalysisResult.relevance_score.desc())
    )
    rows = result.all()

    if not rows:
        message = "今天没有达到阈值的高相关论文，跳过发送"
        logger.info(message)
        return {"sent": False, "skipped": True, "reason": message, "paper_count": 0}

    # Group by paper
    paper_map: dict[int, dict] = {}
    for ar, paper, kw in rows:
        if paper.id not in paper_map:
            paper_map[paper.id] = {
                "title": clean_text(paper.title),
                "authors": clean_text(paper.authors),
                "url": build_paper_url(paper.url, paper.doi),
                "journal": "",
                "score": ar.relevance_score,
                "summary": ar.summary or "",
                "abstract": clean_text(paper.abstract),
                "keywords": [],
            }
        paper_map[paper.id]["keywords"].append(kw.word)

    papers_data = sorted(paper_map.values(), key=lambda x: x["score"], reverse=True)

    html = await build_email_html(papers_data)
    subject = f"[PaperPulse] {len(papers_data)} relevant papers found - {datetime.now().strftime('%Y-%m-%d')}"

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{config.get('sender_name', 'PaperPulse')} <{config['smtp_user']}>"
        msg["To"] = config["recipient"]
        msg.attach(MIMEText(html, "html", "utf-8"))

        with open_smtp_connection(config) as server:
            if int(config.get("smtp_port", 587)) != 465:
                server.starttls()
            server.login(config["smtp_user"], config["smtp_password"])
            server.send_message(msg)

        logger.info(f"Email sent to {config['recipient']}: {len(papers_data)} papers")
        return {"sent": True, "skipped": False, "reason": "", "paper_count": len(papers_data)}
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return {"sent": False, "skipped": False, "reason": str(e), "paper_count": len(papers_data)}
