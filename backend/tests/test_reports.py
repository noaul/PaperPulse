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
from app.services.email_sender import build_email_html
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

    async def test_create_report_can_scope_items_to_current_workflow_papers(self):
        async with SessionLocal() as db:
            keyword = Keyword(word="alloy", enabled=True)
            old_paper = Paper(title="Old matching paper", url="https://example.test/old")
            current_paper = Paper(title="Current matching paper", url="https://example.test/current")
            db.add_all([keyword, old_paper, current_paper])
            await db.commit()
            await db.refresh(keyword)
            await db.refresh(old_paper)
            await db.refresh(current_paper)

            db.add_all([
                AnalysisResult(
                    paper_id=old_paper.id,
                    keyword_id=keyword.id,
                    relevance_score=9.0,
                    summary="Old high score",
                    analyzed_at=datetime.now(timezone.utc),
                ),
                AnalysisResult(
                    paper_id=current_paper.id,
                    keyword_id=keyword.id,
                    relevance_score=6.0,
                    summary="Current workflow score",
                    analyzed_at=datetime.now(timezone.utc),
                ),
            ])
            await db.commit()

            report = await create_report_from_recent_analyses(
                db,
                threshold=6.0,
                source="unit-test",
                paper_ids=[current_paper.id],
            )

            self.assertEqual(1, report.paper_count)
            self.assertIn("Current matching paper", report.markdown)
            self.assertNotIn("Old matching paper", report.markdown)

    async def test_empty_threshold_report_includes_recent_ai_digest(self):
        async with SessionLocal() as db:
            keyword = Keyword(word="nickel alloy", enabled=True)
            paper = Paper(
                title="Below threshold but analyzed paper",
                authors="A. Analyst",
                abstract="Moderately relevant abstract",
                url="https://example.test/below-threshold",
            )
            db.add_all([keyword, paper])
            await db.commit()
            await db.refresh(keyword)
            await db.refresh(paper)

            db.add(AnalysisResult(
                paper_id=paper.id,
                keyword_id=keyword.id,
                relevance_score=6.0,
                summary="AI found moderate relevance below the report threshold",
                analyzed_at=datetime.now(timezone.utc),
            ))
            await db.commit()

            report = await create_report_from_recent_analyses(
                db,
                threshold=7.0,
                source="unit-test",
                paper_ids=[paper.id],
                analyzed_count=1,
                related_count=1,
            )

            self.assertEqual(0, report.paper_count)
            self.assertIn("Below-threshold AI analyses", report.markdown)
            self.assertIn("Below threshold but analyzed paper", report.markdown)
            self.assertIn("AI found moderate relevance", report.markdown)
            self.assertIn("未达到阈值的 AI 分析", report.html)
            self.assertIn("Below threshold but analyzed paper", report.html)

    async def test_empty_email_html_explains_when_no_papers_match_threshold(self):
        html = await build_email_html([], threshold=7.0, analyzed_count=44, related_count=3)

        self.assertIn("未达到报告阈值", html)
        self.assertIn("7.0", html)
        self.assertIn("44", html)
