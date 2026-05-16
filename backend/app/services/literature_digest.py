"""AI literature digest: generate weekly/monthly research trend summaries."""
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import AnalysisResult, Paper, Keyword, Report, ReportItem
from .ai_analyzer import get_ai_config, request_chat_completion

logger = logging.getLogger(__name__)


async def generate_literature_digest(
    db: AsyncSession,
    workspace_id: int,
    days: int = 7,
    min_score: float = 5.0,
    max_papers: int = 30,
) -> str | None:
    """Generate an AI literature digest summarizing recent relevant papers.
    
    Returns markdown text of the digest, or None if insufficient data.
    """
    config = await get_ai_config(db)
    if not config.get("enabled") or not config.get("api_key"):
        return None

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # Get recent high-score analyses
    result = await db.execute(
        select(AnalysisResult, Paper, Keyword)
        .join(Paper, AnalysisResult.paper_id == Paper.id)
        .join(Keyword, AnalysisResult.keyword_id == Keyword.id)
        .where(
            AnalysisResult.workspace_id == workspace_id,
            AnalysisResult.relevance_score >= min_score,
            AnalysisResult.analyzed_at >= cutoff,
        )
        .order_by(desc(AnalysisResult.relevance_score))
        .limit(max_papers)
    )
    rows = result.all()
    if not rows:
        return None

    # Build papers summary for LLM
    papers_text = []
    seen_papers = set()
    for ar, paper, kw in rows:
        if paper.id in seen_papers:
            continue
        seen_papers.add(paper.id)
        papers_text.append(
            f"- [{ar.relevance_score:.1f}] {paper.title}\n"
            f"  关键词: {kw.word} | 摘要: {(ar.summary or '')[:150]}"
        )

    if len(papers_text) < 2:
        return None

    papers_block = "\n".join(papers_text[:max_papers])
    period_label = f"过去{days}天" if days <= 7 else f"过去{days // 7}周"

    prompt = f"""你是学术文献分析专家。以下是{period_label}内与用户研究方向高度相关的论文列表（按相关性排序）：

{papers_block}

请生成一份简洁的中文文献综述摘要（Markdown格式），包含：
1. **研究趋势概述**（2-3句话概括主要研究方向和热点）
2. **重点论文推荐**（选3-5篇最重要的，说明为什么值得关注）
3. **研究建议**（1-2句话，基于趋势给出下一步关注方向）

保持简洁，总字数控制在500字以内。"""

    try:
        digest = await request_chat_completion(
            config,
            [{"role": "user", "content": prompt}],
            max_tokens=1000,
        )
        return digest.strip()
    except Exception as e:
        logger.error(f"Literature digest generation failed: {e}")
        return None
