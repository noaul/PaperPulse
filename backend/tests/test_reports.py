import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch


TEST_DIR = tempfile.TemporaryDirectory()
os.environ["DB_PATH"] = str(Path(TEST_DIR.name) / "paperpulse-reports-test.db")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.database import Base, engine, SessionLocal
from app.models import AnalysisResult, EmailDelivery, Keyword, Paper, Report, ReportItem, Setting
from app.services.report_center import create_report_from_recent_analyses, send_report_email


class ReportCenterTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    async def seed_analysis_data(self):
        async with SessionLocal() as db:
            paper = Paper(
                title="High entropy alloy fatigue",
                authors="A. Researcher",
                abstract="Abstract text",
                url="https://example.test/paper?utm_source=rss",
                published_at=datetime.now(timezone.utc),
            )
            keyword_a = Keyword(word="alloy", enabled=True)
            keyword_b = Keyword(word="fatigue", enabled=True)
            db.add_all([paper, keyword_a, keyword_b])
            await db.commit()
            await db.refresh(paper)
            await db.refresh(keyword_a)
            await db.refresh(keyword_b)
            db.add_all([
                AnalysisResult(
                    paper_id=paper.id,
                    keyword_id=keyword_a.id,
                    relevance_score=8.5,
                    summary="Highly relevant alloy paper",
                    analyzed_at=datetime.now(timezone.utc),
                ),
                AnalysisResult(
                    paper_id=paper.id,
                    keyword_id=keyword_b.id,
                    relevance_score=7.0,
                    summary="Fatigue mechanism discussed",
                    analyzed_at=datetime.now(timezone.utc),
                ),
            ])
            await db.commit()

    async def test_create_report_from_recent_analyses_persists_report_and_deduplicated_items(self):
        await self.seed_analysis_data()

        async with SessionLocal() as db:
            report = await create_report_from_recent_analyses(db, threshold=6.0, source="unit-test")

            self.assertIsNotNone(report.id)
            self.assertEqual("ready", report.status)
            self.assertEqual(1, report.paper_count)
            self.assertEqual(8.5, report.max_relevance_score)
            self.assertIn("High entropy alloy fatigue", report.markdown)
            self.assertIn("alloy", report.markdown)
            self.assertIn("fatigue", report.markdown)

            items_result = await db.execute(select(ReportItem).where(ReportItem.report_id == report.id))
            items = items_result.scalars().all()
            self.assertEqual(1, len(items))
            self.assertEqual(report.id, items[0].report_id)
            self.assertEqual(8.5, items[0].relevance_score)
            self.assertIn("alloy", json.loads(items[0].keywords_json))
            self.assertIn("fatigue", json.loads(items[0].keywords_json))

    async def test_send_report_email_records_skipped_delivery_when_email_disabled(self):
        await self.seed_analysis_data()

        async with SessionLocal() as db:
            report = await create_report_from_recent_analyses(db, threshold=6.0, source="unit-test")
            delivery = await send_report_email(db, report.id)

            self.assertEqual("skipped", delivery.status)
            self.assertIn("邮件未启用", delivery.error_message)
            self.assertEqual(report.id, delivery.report_id)

    async def test_send_report_email_records_successful_delivery(self):
        await self.seed_analysis_data()

        async with SessionLocal() as db:
            db.add(Setting(
                key="email_config",
                value=json.dumps({
                    "enabled": True,
                    "smtp_server": "smtp.example.test",
                    "smtp_port": 587,
                    "smtp_user": "sender@example.test",
                    "smtp_password": "secret",
                    "sender_name": "PaperPulse",
                    "recipient": "reader@example.test",
                }),
            ))
            await db.commit()

            report = await create_report_from_recent_analyses(db, threshold=6.0, source="unit-test")

            with patch("app.services.report_center.open_smtp_connection") as open_smtp:
                delivery = await send_report_email(db, report.id)

            self.assertEqual("sent", delivery.status)
            self.assertEqual("reader@example.test", delivery.recipient)
            self.assertIn("PaperPulse Literature Report", delivery.subject)
            open_smtp.return_value.__enter__.return_value.send_message.assert_called_once()

            persisted = await db.get(EmailDelivery, delivery.id)
            self.assertEqual("sent", persisted.status)
