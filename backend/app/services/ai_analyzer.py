import httpx
import json
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import Paper, Keyword, AnalysisResult, Setting

logger = logging.getLogger(__name__)


async def get_ai_config(db: AsyncSession) -> dict:
    result = await db.execute(select(Setting).where(Setting.key == "ai_config"))
    row = result.scalar_one_or_none()
    if row:
        return json.loads(row.value)
    return {"api_base": "https://api.openai.com/v1", "api_key": "", "model": "gpt-4o-mini", "enabled": True}


async def analyze_paper(db: AsyncSession, paper: Paper, keywords: list[Keyword], config: dict) -> list[AnalysisResult]:
    if not config.get("api_key") or not config.get("enabled"):
        return []

    keyword_list = ", ".join(k.word for k in keywords)
    prompt = f"""You are an academic paper analyst. Given a paper abstract and a list of research keywords, evaluate the relevance.

Keywords: {keyword_list}

Paper Title: {paper.title}
Abstract: {paper.abstract or 'N/A'}

Respond in JSON format:
{{"relevance_score": <0-10>, "matched_keywords": ["keyword1"], "summary": "<brief Chinese summary of why this paper is relevant, 1-2 sentences>"}}

If not relevant at all, score 0 and summary "与研究方向无关".
Respond ONLY with the JSON object, no markdown."""

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{config['api_base'].rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {config['api_key']}", "Content-Type": "application/json"},
                json={
                    "model": config.get("model", "gpt-4o-mini"),
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 500,
                },
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            # Strip markdown code fences if present
            content = content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            data = json.loads(content)
    except Exception as e:
        logger.error(f"AI analysis failed for paper '{paper.title}': {e}")
        return []

    results = []
    matched = data.get("matched_keywords", [])
    score = float(data.get("relevance_score", 0))
    summary = data.get("summary", "")

    for kw in keywords:
        if kw.word.lower() in [m.lower() for m in matched] or score >= 5:
            ar = AnalysisResult(
                paper_id=paper.id,
                keyword_id=kw.id,
                relevance_score=score,
                summary=summary,
            )
            db.add(ar)
            results.append(ar)

    if results:
        await db.commit()

    return results


async def analyze_new_papers(db: AsyncSession) -> list[AnalysisResult]:
    config = await get_ai_config(db)
    if not config.get("enabled") or not config.get("api_key"):
        logger.info("AI analysis disabled or no API key")
        return []

    # Get all enabled keywords
    kw_result = await db.execute(select(Keyword).where(Keyword.enabled == True))
    keywords = kw_result.scalars().all()
    if not keywords:
        logger.info("No keywords configured")
        return []

    # Get papers without analysis
    from sqlalchemy import and_
    analyzed_ids = select(AnalysisResult.paper_id).distinct()
    paper_result = await db.execute(
        select(Paper).where(~Paper.id.in_(analyzed_ids)).order_by(Paper.fetched_at.desc()).limit(50)
    )
    papers = paper_result.scalars().all()

    if not papers:
        logger.info("No new papers to analyze")
        return []

    all_results = []
    for paper in papers:
        results = await analyze_paper(db, paper, keywords, config)
        all_results.extend(results)
        logger.info(f"Analyzed '{paper.title}': {len(results)} matches")

    return all_results
