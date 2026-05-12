import html

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import AnalysisResult, Keyword, Paper
from ..schemas import ZoteroAnalyzeRequest, ZoteroAnalyzeResponse
from ..services.ai_analyzer import analyze_paper, get_ai_config
from ..services.rss_fetcher import clean_text, normalize_paper_url

router = APIRouter(prefix="/api/zotero", tags=["zotero"])


async def get_or_create_zotero_paper(db: AsyncSession, payload: ZoteroAnalyzeRequest) -> Paper:
    normalized_url = normalize_paper_url(payload.url)
    paper = None

    if payload.doi:
        paper = (await db.execute(select(Paper).where(Paper.doi == payload.doi))).scalar_one_or_none()
    if not paper and normalized_url:
        paper = (await db.execute(select(Paper).where(Paper.url == normalized_url))).scalar_one_or_none()

    if paper:
        if not paper.abstract and payload.abstract:
            paper.abstract = clean_text(payload.abstract)
        if not paper.authors and payload.authors:
            paper.authors = clean_text(payload.authors)
        db.add(paper)
        await db.commit()
        await db.refresh(paper)
        return paper

    paper = Paper(
        title=clean_text(payload.title),
        authors=clean_text(payload.authors),
        abstract=clean_text(payload.abstract),
        doi=payload.doi or None,
        url=normalized_url,
        category="zotero",
    )
    db.add(paper)
    await db.commit()
    await db.refresh(paper)
    return paper


def build_zotero_note(payload: ZoteroAnalyzeRequest, score: float, matched_keywords: list[str], summary: str) -> str:
    keyword_text = ", ".join(matched_keywords) if matched_keywords else "无"
    zotero_key = f"<p><b>Zotero Key:</b> {html.escape(payload.zotero_key)}</p>" if payload.zotero_key else ""
    return (
        "<div data-paperpulse-analysis=\"true\">"
        "<h2>PaperPulse AI 分析</h2>"
        f"{zotero_key}"
        f"<p><b>相关性评分:</b> {score:.1f}</p>"
        f"<p><b>匹配关键词:</b> {html.escape(keyword_text)}</p>"
        f"<p><b>摘要:</b> {html.escape(summary or '')}</p>"
        "</div>"
    )


@router.post("/analyze", response_model=ZoteroAnalyzeResponse)
async def analyze_zotero_item(payload: ZoteroAnalyzeRequest, db: AsyncSession = Depends(get_db)):
    config = await get_ai_config(db)
    if not config.get("enabled") or not config.get("api_key"):
        raise HTTPException(400, "AI 未启用或 API Key 为空，请先在 PaperPulse 设置页配置 AI")

    keyword_result = await db.execute(select(Keyword).where(Keyword.enabled == True))
    keywords = keyword_result.scalars().all()
    if not keywords:
        raise HTTPException(400, "未配置启用的主题词，请先在 PaperPulse 关键词页面添加主题词")

    paper = await get_or_create_zotero_paper(db, payload)
    results = await analyze_paper(db, paper, keywords, config, raise_errors=True)

    if results:
        score = max(result.relevance_score for result in results)
        matched_keywords = [
            keyword.word
            for result in results
            for keyword in keywords
            if keyword.id == result.keyword_id
        ]
        summary = results[0].summary or ""
    else:
        score = 0.0
        matched_keywords = []
        summary = "与研究方向无关"

    zotero_tags = [f"PaperPulse:{score:.1f}"]
    if score >= 7:
        zotero_tags.append("PaperPulse:high-relevance")
    elif score >= 5:
        zotero_tags.append("PaperPulse:medium-relevance")
    else:
        zotero_tags.append("PaperPulse:low-relevance")
    zotero_tags.extend(f"PaperPulse:{keyword}" for keyword in matched_keywords)

    return ZoteroAnalyzeResponse(
        success=True,
        paper_id=paper.id,
        analysis_ids=[result.id for result in results if result.id is not None],
        relevance_score=score,
        matched_keywords=matched_keywords,
        summary=summary,
        zotero_tags=zotero_tags,
        note_html=build_zotero_note(payload, score, matched_keywords, summary),
    )
