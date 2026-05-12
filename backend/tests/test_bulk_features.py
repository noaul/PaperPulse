import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


TEST_DIR = tempfile.TemporaryDirectory()
os.environ["DB_PATH"] = str(Path(TEST_DIR.name) / "paperpulse-bulk-test.db")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from httpx import ASGITransport, AsyncClient

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import AnalysisResult, Feed, Keyword, Paper, ReadingQueueItem, Setting


class BulkFeatureApiTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        self.transport = ASGITransport(app=app)
        self.client = AsyncClient(transport=self.transport, base_url="http://testserver")

    async def asyncTearDown(self):
        await self.client.aclose()

    async def test_keywords_bulk_create_splits_lines_commas_and_deduplicates_existing_words(self):
        async with SessionLocal() as db:
            db.add(Keyword(word="battery", category="existing", enabled=True))
            await db.commit()

        response = await self.client.post("/api/keywords/bulk", json={
            "text": "battery\nalloy, fatigue; corrosion\n\n alloy ",
            "category": "materials",
        })

        self.assertEqual(200, response.status_code)
        data = response.json()
        self.assertEqual(3, data["created_count"])
        self.assertEqual(["battery", "alloy"], data["skipped_words"])
        self.assertEqual(["alloy", "fatigue", "corrosion"], [item["word"] for item in data["created"]])

        async with SessionLocal() as db:
            result = await db.execute(select_keywords_ordered())
            words = [keyword.word for keyword in result.scalars().all()]
            self.assertEqual(["alloy", "battery", "corrosion", "fatigue"], words)

    async def test_feeds_fetch_all_refreshes_enabled_feeds_and_persists_latest_fetch_batch(self):
        async with SessionLocal() as db:
            feeds = [
                Feed(name="Feed A", url="https://example.test/a.xml", enabled=True),
                Feed(name="Feed B", url="https://example.test/b.xml", enabled=True),
                Feed(name="Feed C", url="https://example.test/c.xml", enabled=False),
            ]
            db.add_all(feeds)
            await db.commit()
            for feed in feeds:
                await db.refresh(feed)

        async def fake_fetch_feed(db, feed):
            paper = Paper(
                feed_id=feed.id,
                title=f"Paper from {feed.name}",
                url=f"https://example.test/papers/{feed.id}",
            )
            db.add(paper)
            await db.commit()
            await db.refresh(paper)
            return [paper]

        with patch("app.routers.feeds.fetch_feed", fake_fetch_feed):
            response = await self.client.post("/api/feeds/fetch-all")

        self.assertEqual(200, response.status_code)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(2, data["feed_count"])
        self.assertEqual(2, data["new_papers"])
        self.assertEqual(2, len(data["paper_ids"]))

        async with SessionLocal() as db:
            latest = await db.get(Setting, "latest_fetched_paper_ids")
            self.assertIsNotNone(latest)
            self.assertEqual(sorted(data["paper_ids"]), sorted(json.loads(latest.value)))

    async def test_feeds_bulk_delete_removes_requested_feeds(self):
        async with SessionLocal() as db:
            feeds = [
                Feed(name="Delete A", url="https://example.test/delete-a.xml"),
                Feed(name="Keep", url="https://example.test/keep.xml"),
                Feed(name="Delete B", url="https://example.test/delete-b.xml"),
            ]
            db.add_all(feeds)
            await db.commit()
            for feed in feeds:
                await db.refresh(feed)

        response = await self.client.post("/api/feeds/bulk-delete", json={"ids": [feeds[0].id, feeds[2].id, 999]})

        self.assertEqual(200, response.status_code)
        data = response.json()
        self.assertEqual(2, data["deleted_count"])
        self.assertEqual([999], data["missing_ids"])

        async with SessionLocal() as db:
            result = await db.execute(select_feeds_ordered())
            self.assertEqual(["Keep"], [feed.name for feed in result.scalars().all()])

    async def test_add_analysis_result_to_reading_queue_uses_paper_details_and_keyword_tag(self):
        async with SessionLocal() as db:
            paper = Paper(
                title="Relevant alloy paper",
                url="https://example.test/alloy",
                abstract="Alloy abstract",
                authors="A. Researcher",
            )
            keyword = Keyword(word="alloy", category="materials", enabled=True)
            db.add_all([paper, keyword])
            await db.commit()
            await db.refresh(paper)
            await db.refresh(keyword)
            analysis = AnalysisResult(
                paper_id=paper.id,
                keyword_id=keyword.id,
                relevance_score=8.5,
                summary="值得阅读",
            )
            db.add(analysis)
            await db.commit()
            await db.refresh(analysis)

        response = await self.client.post(f"/api/analysis/{analysis.id}/add-to-reading-queue")

        self.assertEqual(200, response.status_code)
        data = response.json()
        self.assertEqual("Relevant alloy paper", data["title"])
        self.assertEqual("https://example.test/alloy", data["url"])
        self.assertEqual("Alloy abstract", data["abstract"])
        self.assertEqual(["alloy"], data["tags"])
        self.assertIn("相关性 8.5", data["notes"])
        self.assertIn("值得阅读", data["notes"])

        duplicate_response = await self.client.post(f"/api/analysis/{analysis.id}/add-to-reading-queue")
        self.assertEqual(200, duplicate_response.status_code)
        self.assertEqual(data["id"], duplicate_response.json()["id"])

        async with SessionLocal() as db:
            count = (await db.execute(select_queue_count())).scalar()
            self.assertEqual(1, count)


def select_keywords_ordered():
    from sqlalchemy import select

    return select(Keyword).order_by(Keyword.word)


def select_feeds_ordered():
    from sqlalchemy import select

    return select(Feed).order_by(Feed.name)


def select_queue_count():
    from sqlalchemy import func, select

    return select(func.count(ReadingQueueItem.id))

if __name__ == "__main__":
    unittest.main()
