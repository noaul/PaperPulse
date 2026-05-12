import os
import sys
import tempfile
import unittest
from pathlib import Path


TEST_DIR = tempfile.TemporaryDirectory()
os.environ["DB_PATH"] = str(Path(TEST_DIR.name) / "paperpulse-reading-queue-test.db")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from httpx import ASGITransport, AsyncClient

from app.database import Base, engine
from app.main import app


class ReadingQueueApiTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        self.transport = ASGITransport(app=app)
        self.client = AsyncClient(transport=self.transport, base_url="http://testserver")

    async def asyncTearDown(self):
        await self.client.aclose()

    async def test_create_item_normalizes_tags_and_defaults_to_unread(self):
        response = await self.client.post("/api/reading-queue", json={
            "title": "Attention Is All You Need",
            "url": "https://arxiv.org/abs/1706.03762",
            "abstract": "Transformer architecture paper.",
            "tags": ["transformer", "LLM", "transformer", " "],
        })

        self.assertEqual(200, response.status_code)
        data = response.json()
        self.assertIsInstance(data["id"], int)
        self.assertEqual("Attention Is All You Need", data["title"])
        self.assertEqual(["transformer", "LLM"], data["tags"])
        self.assertEqual("unread", data["status"])

    async def test_list_items_supports_search_status_and_tag_filters(self):
        first = (await self.client.post("/api/reading-queue", json={
            "title": "Graph RAG Survey",
            "url": "https://example.test/graph",
            "abstract": "Knowledge graph retrieval augmented generation.",
            "tags": ["rag", "graph"],
        })).json()
        await self.client.post("/api/reading-queue", json={
            "title": "Battery alloy notes",
            "url": "https://example.test/alloy",
            "abstract": "A materials paper about fatigue.",
            "tags": ["materials"],
        })
        await self.client.put(f"/api/reading-queue/{first['id']}", json={"status": "read"})

        search_result = (await self.client.get("/api/reading-queue", params={"search": "retrieval"})).json()
        self.assertEqual(1, search_result["total"])
        self.assertEqual("Graph RAG Survey", search_result["items"][0]["title"])

        tag_result = (await self.client.get("/api/reading-queue", params={"tag": "materials"})).json()
        self.assertEqual(1, tag_result["total"])
        self.assertEqual("Battery alloy notes", tag_result["items"][0]["title"])

        combined_result = (await self.client.get(
            "/api/reading-queue",
            params={"status": "read", "tag": "rag"},
        )).json()
        self.assertEqual(1, combined_result["total"])
        self.assertEqual("Graph RAG Survey", combined_result["items"][0]["title"])

    async def test_update_and_delete_item(self):
        created = (await self.client.post("/api/reading-queue", json={
            "title": "Old title",
            "url": "https://example.test/old",
            "abstract": "Old abstract",
            "tags": ["old"],
        })).json()

        update_response = await self.client.put(f"/api/reading-queue/{created['id']}", json={
            "title": "New title",
            "status": "read",
            "tags": ["new", "paper"],
        })

        self.assertEqual(200, update_response.status_code)
        updated = update_response.json()
        self.assertEqual("New title", updated["title"])
        self.assertEqual("read", updated["status"])
        self.assertEqual(["new", "paper"], updated["tags"])

        delete_response = await self.client.delete(f"/api/reading-queue/{created['id']}")
        self.assertEqual(200, delete_response.status_code)
        list_response = (await self.client.get("/api/reading-queue")).json()
        self.assertEqual(0, list_response["total"])


if __name__ == "__main__":
    unittest.main()
