import os
import sys
import tempfile
import unittest
from pathlib import Path


TEST_DIR = tempfile.TemporaryDirectory()
os.environ["DB_PATH"] = str(Path(TEST_DIR.name) / "paperpulse-workspaces-test.db")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from httpx import ASGITransport, AsyncClient

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import Feed, Keyword


class WorkspaceApiTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        self.transport = ASGITransport(app=app)
        self.client = AsyncClient(transport=self.transport, base_url="http://testserver")

    async def asyncTearDown(self):
        await self.client.aclose()

    async def test_default_workspace_is_available_for_existing_single_workspace_clients(self):
        response = await self.client.get("/api/workspaces")

        self.assertEqual(200, response.status_code)
        data = response.json()
        self.assertGreaterEqual(len(data), 1)
        self.assertTrue(any(item["is_default"] for item in data))

    async def test_feeds_and_keywords_are_isolated_by_workspace_header(self):
        alloy = (await self.client.post("/api/workspaces", json={"name": "高温合金"})).json()
        biomedical = (await self.client.post("/api/workspaces", json={"name": "另一个工作区"})).json()
        alloy_headers = {"X-Workspace-Id": str(alloy["id"])}
        other_headers = {"X-Workspace-Id": str(biomedical["id"])}

        feed_payload = {
            "name": "Shared feed",
            "url": "https://example.test/shared.xml",
            "journal_name": "Shared Journal",
        }
        first_feed = await self.client.post("/api/feeds", json=feed_payload, headers=alloy_headers)
        second_feed = await self.client.post("/api/feeds", json=feed_payload, headers=other_headers)

        self.assertEqual(200, first_feed.status_code)
        self.assertEqual(200, second_feed.status_code)

        await self.client.post(
            "/api/keywords",
            json={"word": "fatigue", "category": "mechanics"},
            headers=alloy_headers,
        )
        await self.client.post(
            "/api/keywords",
            json={"word": "fatigue", "category": "different"},
            headers=other_headers,
        )

        alloy_feeds = (await self.client.get("/api/feeds", headers=alloy_headers)).json()
        other_feeds = (await self.client.get("/api/feeds", headers=other_headers)).json()
        self.assertEqual(1, len(alloy_feeds))
        self.assertEqual(1, len(other_feeds))
        self.assertNotEqual(alloy_feeds[0]["id"], other_feeds[0]["id"])

        alloy_keywords = (await self.client.get("/api/keywords", headers=alloy_headers)).json()
        other_keywords = (await self.client.get("/api/keywords", headers=other_headers)).json()
        self.assertEqual(["mechanics"], [item["category"] for item in alloy_keywords])
        self.assertEqual(["different"], [item["category"] for item in other_keywords])

        async with SessionLocal() as db:
            all_feeds = (await db.execute(select_all(Feed))).scalars().all()
            all_keywords = (await db.execute(select_all(Keyword))).scalars().all()
            self.assertEqual(2, len(all_feeds))
            self.assertEqual(2, len(all_keywords))


def select_all(model):
    from sqlalchemy import select

    return select(model)


if __name__ == "__main__":
    unittest.main()
