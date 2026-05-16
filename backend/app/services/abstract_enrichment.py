"""Abstract enrichment: fetch real abstracts from Crossref/OpenAlex when RSS only has snippets."""
import logging
import httpx
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Paper

logger = logging.getLogger(__name__)

_CROSSREF_URL = "https://api.crossref.org/works/{doi}"
_OPENALEX_URL = "https://api.openalex.org/works/doi:{doi}"
_TIMEOUT = 15


async def enrich_abstract_from_crossref(doi: str) -> str | None:
    """Try fetching abstract from Crossref."""
    if not doi:
        return None
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                _CROSSREF_URL.format(doi=doi),
                headers={"User-Agent": "PaperPulse/1.0 (mailto:paperpulse@example.com)"},
            )
            if resp.status_code != 200:
                return None
            data = resp.json().get("message", {})
            abstract = data.get("abstract", "")
            if abstract and len(abstract) > 50:
                # Crossref abstracts often have JATS XML tags
                import re
                clean = re.sub(r"<[^>]+>", "", abstract).strip()
                return clean if len(clean) > 50 else None
    except Exception as e:
        logger.debug(f"Crossref enrichment failed for {doi}: {e}")
    return None


async def enrich_abstract_from_openalex(doi: str) -> str | None:
    """Try fetching abstract from OpenAlex inverted index."""
    if not doi:
        return None
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                _OPENALEX_URL.format(doi=doi),
                headers={"User-Agent": "PaperPulse/1.0"},
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            # OpenAlex stores abstracts as inverted index
            inv_idx = data.get("abstract_inverted_index")
            if not inv_idx:
                return None
            # Reconstruct text from inverted index
            positions: list[tuple[int, str]] = []
            for word, pos_list in inv_idx.items():
                for pos in pos_list:
                    positions.append((pos, word))
            positions.sort()
            text = " ".join(w for _, w in positions)
            return text if len(text) > 50 else None
    except Exception as e:
        logger.debug(f"OpenAlex enrichment failed for {doi}: {e}")
    return None


async def enrich_paper_abstract(db: AsyncSession, paper: Paper) -> bool:
    """Attempt to enrich a paper's abstract if it's missing or too short. Returns True if updated."""
    if paper.abstract and len(paper.abstract.strip()) > 100:
        return False
    if not paper.doi:
        return False

    abstract = await enrich_abstract_from_crossref(paper.doi)
    if not abstract:
        abstract = await enrich_abstract_from_openalex(paper.doi)
    if not abstract:
        return False

    paper.abstract = abstract
    db.add(paper)
    await db.commit()
    logger.info(f"Enriched abstract for paper '{paper.title[:60]}' via DOI {paper.doi}")
    return True


async def enrich_recent_papers(db: AsyncSession, workspace_id: int, limit: int = 50) -> int:
    """Enrich abstracts for recent papers that have DOI but short/missing abstract."""
    from sqlalchemy import func
    result = await db.execute(
        select(Paper)
        .where(
            Paper.workspace_id == workspace_id,
            Paper.doi.isnot(None),
            Paper.doi != "",
            (func.length(Paper.abstract) < 100) | (Paper.abstract.is_(None)),
        )
        .order_by(Paper.fetched_at.desc())
        .limit(limit)
    )
    papers = result.scalars().all()
    enriched = 0
    for paper in papers:
        if await enrich_paper_abstract(db, paper):
            enriched += 1
    return enriched
