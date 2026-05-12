import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


TEST_DIR = tempfile.TemporaryDirectory()
os.environ["DB_PATH"] = str(Path(TEST_DIR.name) / "paperpulse-webdav-test.db")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import Base, SessionLocal, engine
from app.models import AnalysisResult, Feed, Keyword, Paper, Setting
from app.services.webdav_sync import export_data


class WebdavSyncTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    async def test_export_data_includes_papers_and_analysis_results(self):
        async with SessionLocal() as db:
            feed = Feed(name="Feed", url="https://example.test/feed.xml", journal_name="Journal")
            keyword = Keyword(word="alloy", category="materials", enabled=True)
            db.add_all([feed, keyword])
            await db.commit()
            await db.refresh(feed)
            await db.refresh(keyword)

            paper = Paper(
                feed_id=feed.id,
                title="Alloy paper",
                url="https://example.test/paper",
                abstract="Abstract",
                doi="10.1000/test",
            )
            db.add(paper)
            await db.commit()
            await db.refresh(paper)

            db.add(AnalysisResult(
                paper_id=paper.id,
                keyword_id=keyword.id,
                relevance_score=8.2,
                summary="Highly relevant",
            ))
            db.add(Setting(
                key="webdav_config",
                value=json.dumps({
                    "url": "https://webdav.example.test",
                    "username": "u",
                    "password": "p",
                    "remote_path": "/PaperPulse/",
                }),
            ))
            await db.commit()

            uploaded = {}

            class FakeClient:
                def check(self, path):
                    return True

                def upload_sync(self, remote_path, content):
                    uploaded["remote_path"] = remote_path
                    uploaded["data"] = json.loads(content.read().decode("utf-8"))

            with patch("app.services.webdav_sync._get_client", return_value=FakeClient()):
                exported = await export_data(db)

        self.assertTrue(exported)
        self.assertEqual("/PaperPulse/paperpulse_backup.json", uploaded["remote_path"])
        self.assertEqual("Alloy paper", uploaded["data"]["papers"][0]["title"])
        self.assertEqual("10.1000/test", uploaded["data"]["papers"][0]["doi"])
        self.assertEqual(8.2, uploaded["data"]["analysis_results"][0]["relevance_score"])
        self.assertEqual("alloy", uploaded["data"]["analysis_results"][0]["keyword_word"])
        self.assertEqual("10.1000/test", uploaded["data"]["analysis_results"][0]["paper_doi"])


if __name__ == "__main__":
    unittest.main()
