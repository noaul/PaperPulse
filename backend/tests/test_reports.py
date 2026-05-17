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

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.database import Base, engine, SessionLocal
from app.models import AnalysisResult, EmailDelivery, EmailTopicRule, Keyword, Paper, Report, ReportItem, Setting
from app.main import app
from app.services.email_sender import build_email_html
from app.services.report_center import create_and_send_recent_report, create_report_from_recent_analyses, send_report_email


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

    async def test_create_report_from_recent_analyses_includes_positive_scores(self):
        await self.seed_analysis_data()

        async with SessionLocal() as db:
            report = await create_report_from_recent_analyses(db, source="unit-test")

            self.assertIsNotNone(report.id)
            self.assertEqual("ready", report.status)
            self.assertEqual(1, report.paper_count)
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
            report = await create_report_from_recent_analyses(db, source="unit-test")
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

            report = await create_report_from_recent_analyses(db, source="unit-test")

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
                source="unit-test",
                paper_ids=[current_paper.id],
            )

            self.assertEqual(1, report.paper_count)
            self.assertIn("Current matching paper", report.markdown)
            self.assertNotIn("Old matching paper", report.markdown)

    async def test_report_includes_low_quality_positive_score_items(self):
        async with SessionLocal() as db:
            keyword = Keyword(word="nickel alloy", enabled=True)
            paper = Paper(
                title="Low quality but relevant paper",
                authors="A. Analyst",
                abstract="Moderately relevant abstract",
                url="https://example.test/low-quality",
            )
            db.add_all([keyword, paper])
            await db.commit()
            await db.refresh(keyword)
            await db.refresh(paper)

            db.add(AnalysisResult(
                paper_id=paper.id,
                keyword_id=keyword.id,
                relevance_score=6.0,
                summary="AI found a relevant but lower quality paper",
                analyzed_at=datetime.now(timezone.utc),
            ))
            await db.commit()

            report = await create_report_from_recent_analyses(
                db,
                source="unit-test",
                paper_ids=[paper.id],
                analyzed_count=1,
                related_count=1,
            )

            self.assertEqual(1, report.paper_count)
            self.assertIn("Low quality but relevant paper", report.markdown)
            self.assertIn("AI found a relevant", report.markdown)
            self.assertNotIn("Below-threshold", report.markdown)
            self.assertNotIn("阈值", report.html)

    async def test_report_excludes_zero_score_items(self):
        async with SessionLocal() as db:
            keyword = Keyword(word="alloy", enabled=True)
            paper = Paper(title="Zero score paper", url="https://example.test/zero")
            db.add_all([keyword, paper])
            await db.commit()
            await db.refresh(keyword)
            await db.refresh(paper)
            db.add(AnalysisResult(
                paper_id=paper.id,
                keyword_id=keyword.id,
                relevance_score=0.0,
                summary="与研究方向无关",
                analyzed_at=datetime.now(timezone.utc),
            ))
            await db.commit()

            report = await create_report_from_recent_analyses(
                db,
                source="unit-test",
                paper_ids=[paper.id],
            )

            items = (await db.execute(select(ReportItem).where(ReportItem.report_id == report.id))).scalars().all()
            self.assertEqual(0, report.paper_count)
            self.assertEqual([], items)
            self.assertNotIn("Zero score paper", report.markdown)
            self.assertNotIn("Zero score paper", report.html)

    async def test_create_and_send_report_skips_email_when_only_zero_score_items_exist(self):
        async with SessionLocal() as db:
            keyword = Keyword(word="alloy", enabled=True)
            paper = Paper(title="Zero score email paper", url="https://example.test/zero-email")
            db.add_all([keyword, paper])
            db.add(Setting(
                key="email_config",
                value=json.dumps({
                    "enabled": True,
                    "smtp_server": "smtp.example.test",
                    "smtp_port": 587,
                    "smtp_user": "sender@example.test",
                    "smtp_password": "secret",
                    "recipient": "reader@example.test",
                }),
            ))
            await db.commit()
            await db.refresh(keyword)
            await db.refresh(paper)
            db.add(AnalysisResult(
                paper_id=paper.id,
                keyword_id=keyword.id,
                relevance_score=0.0,
                summary="与研究方向无关",
                analyzed_at=datetime.now(timezone.utc),
            ))
            await db.commit()

            with patch("app.services.report_center.open_smtp_connection") as open_smtp:
                result = await create_and_send_recent_report(
                    db,
                    source="unit-test",
                    paper_ids=[paper.id],
                )

            deliveries = (await db.execute(select(EmailDelivery))).scalars().all()
            self.assertFalse(result["sent"])
            self.assertTrue(result["skipped"])
            self.assertEqual(0, result["paper_count"])
            self.assertEqual([], deliveries)
            open_smtp.assert_not_called()

    async def test_topic_report_excludes_zero_score_items(self):
        async with SessionLocal() as db:
            keyword = Keyword(word="alloy", enabled=True)
            paper = Paper(title="Zero score topic paper", url="https://example.test/zero-topic")
            db.add_all([keyword, paper])
            await db.commit()
            await db.refresh(keyword)
            await db.refresh(paper)

            rule = EmailTopicRule(name="Alloy topic", rule_type="OR", workspace_id=1)
            rule.set_keyword_ids([keyword.id])
            db.add(rule)
            db.add(AnalysisResult(
                paper_id=paper.id,
                keyword_id=keyword.id,
                relevance_score=0.0,
                summary="与研究方向无关",
                analyzed_at=datetime.now(timezone.utc),
            ))
            await db.commit()
            await db.refresh(rule)

            report = await create_report_from_recent_analyses(
                db,
                source="unit-test",
                topic_rule=rule,
                workspace_id=1,
            )

            self.assertEqual(0, report.paper_count)
            self.assertNotIn("Zero score topic paper", report.markdown)

    async def test_empty_email_html_explains_when_no_positive_papers_match(self):
        html = await build_email_html([], analyzed_count=44, related_count=3)

        self.assertIn("没有可发送的论文", html)
        self.assertNotIn("阈值", html)
        self.assertNotIn("7.0", html)
        self.assertIn("44", html)

    async def test_build_email_html_escapes_dynamic_paper_fields(self):
        html = await build_email_html([{
            "title": "<script>alert(1)</script>",
            "authors": "A <b>Author</b>",
            "journal": "J & Co",
            "url": "https://example.test/paper?x=<bad>&y=\"quote\"",
            "score": 8.0,
            "keywords": ["<kw>", "alloy&fatigue"],
            "summary": "<img src=x onerror=alert(1)>",
            "abstract": "Abstract with <em>markup</em>",
        }])

        self.assertNotIn("<script>", html)
        self.assertNotIn("<b>Author</b>", html)
        self.assertNotIn("<img", html)
        self.assertNotIn("<em>markup</em>", html)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)
        self.assertIn("A &lt;b&gt;Author&lt;/b&gt;", html)
        self.assertIn("J &amp; Co", html)
        self.assertIn("https://example.test/paper?x=&lt;bad&gt;&amp;y=&quot;quote&quot;", html)
        self.assertIn("&lt;kw&gt;", html)
        self.assertIn("alloy&amp;fatigue", html)


class ReportApiTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        self.transport = ASGITransport(app=app)
        self.client = AsyncClient(transport=self.transport, base_url="http://testserver")

    async def asyncTearDown(self):
        await self.client.aclose()

    async def test_delete_report_removes_report_items_and_deliveries(self):
        async with SessionLocal() as db:
            report = Report(title="Delete me", source="unit-test", status="ready", paper_count=1, workspace_id=1)
            db.add(report)
            await db.flush()
            item = ReportItem(report_id=report.id, workspace_id=1, title="Paper", relevance_score=4.0)
            delivery = EmailDelivery(report_id=report.id, workspace_id=1, recipient="reader@example.test", subject="Report")
            db.add_all([item, delivery])
            await db.commit()
            await db.refresh(report)
            report_id = report.id
            item_id = item.id
            delivery_id = delivery.id

        response = await self.client.delete(f"/api/reports/{report_id}")

        self.assertEqual(200, response.status_code)
        self.assertEqual({"success": True}, response.json())
        get_response = await self.client.get(f"/api/reports/{report_id}")
        self.assertEqual(404, get_response.status_code)
        async with SessionLocal() as db:
            self.assertIsNone(await db.get(Report, report_id))
            self.assertIsNone(await db.get(ReportItem, item_id))
            self.assertIsNone(await db.get(EmailDelivery, delivery_id))
