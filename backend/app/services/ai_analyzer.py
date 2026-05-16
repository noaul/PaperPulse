import asyncio
import hashlib
import httpx
import json
import logging
import os
import re
from collections.abc import Awaitable, Callable
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import Paper, Keyword, AnalysisResult, Setting
from .rss_fetcher import get_latest_fetched_paper_ids

logger = logging.getLogger(__name__)

DEFAULT_AI_CONFIG = {
    "api_base": "https://api.openai.com/v1",
    "api_key": "",
    "model": "gpt-4o-mini",
    "reasoning_effort": "xhigh",
    "enabled": True,
}

# Concurrency control for LLM calls
_AI_CONCURRENCY = int(os.environ.get("AI_CONCURRENCY", "4"))
_ai_semaphore = asyncio.Semaphore(_AI_CONCURRENCY)
_AI_MAX_RETRIES = 1

AnalysisProgressCallback = Callable[[dict], Awaitable[None]]
AnalysisControlCallback = Callable[[], Awaitable[None]]


def build_chat_completions_url(api_base: str) -> str:
    """Accept either an API base URL or a full chat completions endpoint."""
    normalized = (api_base or "").strip().rstrip("/")
    if not normalized:
        raise ValueError("AI API 地址为空")

    if normalized.endswith("/chat/completions"):
        return normalized

    path = normalized.split("://", 1)[-1].split("/", 1)
    url_path = f"/{path[1]}" if len(path) > 1 else ""
    if re.search(r"/(?:v\d+(?:beta)?|api/v\d+)$", url_path, re.IGNORECASE):
        return f"{normalized}/chat/completions"

    return f"{normalized}/v1/chat/completions"


def build_responses_url(api_base: str) -> str:
    """Accept either an API base URL or a full responses endpoint."""
    normalized = (api_base or "").strip().rstrip("/")
    if not normalized:
        raise ValueError("AI API 地址为空")

    if normalized.endswith("/responses"):
        return normalized

    path = normalized.split("://", 1)[-1].split("/", 1)
    url_path = f"/{path[1]}" if len(path) > 1 else ""
    if re.search(r"/(?:v\d+(?:beta)?|api/v\d+)$", url_path, re.IGNORECASE):
        return f"{normalized}/responses"

    return f"{normalized}/v1/responses"


def uses_responses_api(api_base: str) -> bool:
    return (api_base or "").strip().rstrip("/").endswith("/responses")


def build_ai_request(
    config: dict,
    messages: list[dict],
    max_tokens: int = 500,
    temperature: float = 0.1,
) -> tuple[str, dict]:
    if uses_responses_api(config.get("api_base", "")):
        payload = {
            "model": config.get("model", DEFAULT_AI_CONFIG["model"]),
            "input": messages,
            "max_output_tokens": max_tokens,
        }
        effort = (config.get("reasoning_effort") or DEFAULT_AI_CONFIG["reasoning_effort"]).strip()
        if effort and effort != "none":
            payload["reasoning"] = {"effort": effort}
        return build_responses_url(config.get("api_base", "")), payload

    return build_chat_completions_url(config.get("api_base", "")), {
        "model": config.get("model", DEFAULT_AI_CONFIG["model"]),
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }


def extract_response_text(data: dict) -> str:
    if "choices" in data:
        return data["choices"][0]["message"]["content"]

    if data.get("output_text"):
        return data["output_text"]

    for output in data.get("output", []):
        for content in output.get("content", []):
            if content.get("text"):
                return content["text"]

    raise ValueError("AI 响应中未找到文本内容")


def extract_json_object(content: str) -> dict:
    content = content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start >= 0 and end > start:
            return json.loads(content[start:end + 1])
        raise


async def request_chat_completion(config: dict, messages: list[dict], max_tokens: int = 500) -> str:
    url, payload = build_ai_request(config, messages, max_tokens=max_tokens)
    last_err = None
    for attempt in range(_AI_MAX_RETRIES + 1):
        try:
            async with _ai_semaphore:
                async with httpx.AsyncClient(timeout=60) as client:
                    resp = await client.post(
                        url,
                        headers={"Authorization": f"Bearer {config['api_key']}", "Content-Type": "application/json"},
                        json=payload,
                    )
                    resp.raise_for_status()
                    return extract_response_text(resp.json())
        except (httpx.HTTPStatusError, httpx.TimeoutException, ValueError) as e:
            last_err = e
            if attempt < _AI_MAX_RETRIES:
                await asyncio.sleep(1 * (attempt + 1))
    raise last_err  # type: ignore


async def get_ai_config(db: AsyncSession) -> dict:
    result = await db.execute(select(Setting).where(Setting.key == "ai_config"))
    row = result.scalar_one_or_none()
    if row:
        return json.loads(row.value)
    return DEFAULT_AI_CONFIG.copy()


class _AnalysisResponse:
    """Validated LLM analysis response."""
    def __init__(self, score: float, matched: list[str], summary: str):
        self.score = max(0.0, min(10.0, score))
        self.matched = [str(k).strip() for k in matched if str(k).strip()]
        self.summary = str(summary or "")[:500]

    @classmethod
    def from_raw(cls, data: dict) -> "_AnalysisResponse":
        score = float(data.get("relevance_score", 0))
        matched = data.get("matched_keywords", [])
        if not isinstance(matched, list):
            matched = []
        summary = data.get("summary", "")
        return cls(score, matched, summary)


async def analyze_paper(
    db: AsyncSession,
    paper: Paper,
    keywords: list[Keyword],
    config: dict,
    *,
    raise_errors: bool = False,
) -> list[AnalysisResult]:
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
        content = await request_chat_completion(config, [{"role": "user", "content": prompt}], max_tokens=500)
        data = extract_json_object(content)
    except Exception as e:
        logger.error(f"AI analysis failed for paper '{paper.title}': {e}")
        if raise_errors:
            raise RuntimeError(f"AI 分析失败：{paper.title[:80]} - {e}") from e
        return []

    try:
        parsed = _AnalysisResponse.from_raw(data)
    except (TypeError, ValueError, KeyError) as e:
        logger.error(f"AI response validation failed for '{paper.title}': {e}")
        if raise_errors:
            raise RuntimeError(f"AI 响应格式错误：{paper.title[:80]}") from e
        return []

    results = []
    matched_normalized = {m.lower() for m in parsed.matched}

    for kw in keywords:
        if kw.word.strip().lower() in matched_normalized:
            ar = AnalysisResult(
                paper_id=paper.id,
                keyword_id=kw.id,
                workspace_id=paper.workspace_id,
                relevance_score=parsed.score,
                summary=parsed.summary,
            )
            db.add(ar)
            results.append(ar)

    if results:
        await db.commit()

    return results


_BATCH_SIZE = int(os.environ.get("AI_BATCH_SIZE", "5"))


async def analyze_papers_batch(
    db: AsyncSession,
    papers: list[Paper],
    keywords: list[Keyword],
    config: dict,
    *,
    raise_errors: bool = False,
) -> list[AnalysisResult]:
    """Analyze multiple papers in one LLM call to reduce token overhead."""
    if not config.get("api_key") or not config.get("enabled") or not papers:
        return []

    keyword_list = ", ".join(k.word for k in keywords)
    papers_block = "\n".join(
        f"[{i}] Title: {p.title}\n    Abstract: {(p.abstract or 'N/A')[:300]}"
        for i, p in enumerate(papers)
    )
    prompt = f"""You are an academic paper analyst. Evaluate {len(papers)} papers against research keywords.

Keywords: {keyword_list}

Papers:
{papers_block}

Respond with a JSON array, one object per paper in order:
[{{"index": 0, "relevance_score": <0-10>, "matched_keywords": ["kw"], "summary": "<1-2 sentence Chinese summary>"}}, ...]

For irrelevant papers: score 0, summary "与研究方向无关", matched_keywords [].
Respond ONLY with the JSON array."""

    try:
        max_tokens = 200 * len(papers)
        content = await request_chat_completion(config, [{"role": "user", "content": prompt}], max_tokens=max_tokens)
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        arr = json.loads(content)
        if not isinstance(arr, list):
            arr = [arr]
    except Exception as e:
        logger.warning(f"Batch analysis failed, falling back to individual: {e}")
        all_results = []
        for paper in papers:
            all_results.extend(await analyze_paper(db, paper, keywords, config, raise_errors=raise_errors))
        return all_results

    all_results = []
    for item in arr:
        try:
            idx = int(item.get("index", -1))
            if idx < 0 or idx >= len(papers):
                continue
            parsed = _AnalysisResponse.from_raw(item)
            paper = papers[idx]
            matched_normalized = {m.lower() for m in parsed.matched}
            for kw in keywords:
                if kw.word.strip().lower() in matched_normalized:
                    ar = AnalysisResult(
                        paper_id=paper.id, keyword_id=kw.id,
                        workspace_id=paper.workspace_id,
                        relevance_score=parsed.score, summary=parsed.summary,
                    )
                    db.add(ar)
                    all_results.append(ar)
        except (TypeError, ValueError, KeyError):
            continue

    if all_results:
        await db.commit()
    return all_results


async def analyze_new_papers(
    db: AsyncSession,
    progress_callback: AnalysisProgressCallback | None = None,
    control_callback: AnalysisControlCallback | None = None,
    *,
    paper_ids: list[int] | None = None,
    workspace_id: int | None = None,
    raise_errors: bool = False,
) -> list[AnalysisResult]:
    config = await get_ai_config(db)
    if not config.get("enabled") or not config.get("api_key"):
        message = "AI 未启用或 API Key 为空，请先到设置页配置 AI"
        logger.info(message)
        if raise_errors:
            raise RuntimeError(message)
        return []

    # Get all enabled keywords
    kw_query = select(Keyword).where(Keyword.enabled == True)
    if workspace_id is not None:
        kw_query = kw_query.where(Keyword.workspace_id == workspace_id)
    kw_result = await db.execute(kw_query)
    keywords = kw_result.scalars().all()
    if not keywords:
        message = "未配置启用的主题词，请先在关键词页面添加主题词"
        logger.info(message)
        if raise_errors:
            raise RuntimeError(message)
        return []

    # Get papers without analysis. Fetch/analyze workflows pass paper_ids so
    # progress total tracks only the papers fetched in the current run.
    # Manual analysis uses the latest persisted fetch batch when available.
    if paper_ids is None:
        paper_ids = await get_latest_fetched_paper_ids(db, workspace_id=workspace_id)

    analyzed_ids = select(AnalysisResult.paper_id).distinct()
    if workspace_id is not None:
        analyzed_ids = analyzed_ids.where(AnalysisResult.workspace_id == workspace_id)
    paper_query = select(Paper).where(~Paper.id.in_(analyzed_ids))
    if workspace_id is not None:
        paper_query = paper_query.where(Paper.workspace_id == workspace_id)
    if paper_ids is not None:
        if not paper_ids:
            papers = []
        else:
            paper_query = paper_query.where(Paper.id.in_(paper_ids))
            paper_result = await db.execute(paper_query.order_by(Paper.fetched_at.desc()))
            papers = paper_result.scalars().all()
    else:
        paper_result = await db.execute(paper_query.order_by(Paper.fetched_at.desc()))
        papers = paper_result.scalars().all()

    total = len(papers)
    analyzed_count = 0
    related_count = 0
    if progress_callback:
        await progress_callback({
            "analysis_total": total,
            "analysis_analyzed": analyzed_count,
            "analysis_related": related_count,
            "analysis_results": 0,
            "analysis_current_title": "",
            "literature_summary": "",
        })
    if control_callback:
        await control_callback()

    if not papers:
        logger.info("No new papers to analyze")
        return []

    all_results = []
    for paper in papers:
        if control_callback:
            await control_callback()
        results = await analyze_paper(db, paper, keywords, config, raise_errors=raise_errors)
        if control_callback:
            await control_callback()
        all_results.extend(results)
        analyzed_count += 1
        if results:
            related_count += 1
        if progress_callback:
            await progress_callback({
                "analysis_total": total,
                "analysis_analyzed": analyzed_count,
                "analysis_related": related_count,
                "analysis_results": len(all_results),
                "analysis_current_title": paper.title,
            })
        logger.info(f"Analyzed '{paper.title}': {len(results)} matches")

    return all_results
