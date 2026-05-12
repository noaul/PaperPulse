import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


TEST_DIR = tempfile.TemporaryDirectory()
os.environ["DB_PATH"] = str(Path(TEST_DIR.name) / "paperpulse-zotero-test.db")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import AnalysisResult, Keyword, Paper, Setting


class ZoteroApiTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        self.transport = ASGITransport(app=app)
        self.client = AsyncClient(transport=self.transport, base_url="http://testserver")

    async def asyncTearDown(self):
        await self.client.aclose()

    async def test_analyze_zotero_item_returns_ai_result_and_persists_paper(self):
        async with SessionLocal() as db:
            db.add(Setting(
                key="ai_config",
                value=json.dumps({
                    "enabled": True,
                    "api_key": "test-key",
                    "api_base": "http://ai.test",
                    "model": "test-model",
                }),
            ))
            db.add(Keyword(word="alloy", category="materials", enabled=True))
            await db.commit()

        async def fake_request_chat_completion(config, messages, max_tokens=500):
            return '{"relevance_score": 8.5, "matched_keywords": ["alloy"], "summary": "这篇论文与合金研究相关。"}'

        with patch("app.services.ai_analyzer.request_chat_completion", fake_request_chat_completion):
            response = await self.client.post("/api/zotero/analyze", json={
                "zotero_key": "ABCD1234",
                "title": "Alloy fatigue from Zotero feed",
                "abstract": "A study about alloy fatigue mechanisms.",
                "url": "https://example.test/zotero?utm_source=rss",
                "authors": "A. Researcher",
                "tags": ["zotero-feed"],
            })

        self.assertEqual(200, response.status_code)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(8.5, data["relevance_score"])
        self.assertEqual(["alloy"], data["matched_keywords"])
        self.assertIn("合金研究", data["summary"])
        self.assertEqual("PaperPulse:8.5", data["zotero_tags"][0])
        self.assertIn("PaperPulse AI 分析", data["note_html"])

        async with SessionLocal() as db:
            paper = (await db.execute(select(Paper).where(Paper.title == "Alloy fatigue from Zotero feed"))).scalar_one()
            self.assertEqual("https://example.test/zotero", paper.url)
            result = (
                await db.execute(select(AnalysisResult).where(AnalysisResult.paper_id == paper.id))
            ).scalar_one()
            self.assertEqual(8.5, result.relevance_score)

    async def test_analyze_zotero_item_reuses_existing_paper_by_url(self):
        async with SessionLocal() as db:
            db.add(Setting(
                key="ai_config",
                value=json.dumps({"enabled": True, "api_key": "test-key", "api_base": "http://ai.test"}),
            ))
            db.add(Keyword(word="battery", enabled=True))
            paper = Paper(title="Existing title", url="https://example.test/existing")
            db.add(paper)
            await db.commit()
            await db.refresh(paper)
            existing_id = paper.id

        async def fake_request_chat_completion(config, messages, max_tokens=500):
            return '{"relevance_score": 6, "matched_keywords": ["battery"], "summary": "相关"}'

        with patch("app.services.ai_analyzer.request_chat_completion", fake_request_chat_completion):
            response = await self.client.post("/api/zotero/analyze", json={
                "title": "Changed title",
                "abstract": "Battery paper",
                "url": "https://example.test/existing",
            })

        self.assertEqual(200, response.status_code)
        async with SessionLocal() as db:
            papers = (await db.execute(select(Paper))).scalars().all()
            self.assertEqual(1, len(papers))
            self.assertEqual(existing_id, papers[0].id)


if __name__ == "__main__":
    unittest.main()
