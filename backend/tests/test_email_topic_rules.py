import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch


TEST_DIR = tempfile.TemporaryDirectory()
os.environ["DB_PATH"] = str(Path(TEST_DIR.name) / "paperpulse-topic-rules-test.db")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.topic_rule_engine import evaluate_rule
from app.database import Base, SessionLocal, engine
from app.models import AnalysisResult, EmailTopicRule, Keyword, Paper, ReportItem
from app.services.report_center import create_and_send_recent_report, create_report_from_recent_analyses


class EmailTopicRuleEngineTest(unittest.TestCase):
    def test_or_rule_matches_any_positive_required_keyword(self):
        self.assertTrue(evaluate_rule(
            "OR",
            required_keyword_ids=[1, 2],
            exclude_keyword_ids=[],
            paper_keyword_scores={2: 1.5},
        ))
        self.assertFalse(evaluate_rule(
            "OR",
            required_keyword_ids=[1, 2],
            exclude_keyword_ids=[],
            paper_keyword_scores={2: 0.0},
        ))

    def test_and_rule_requires_all_keywords_with_positive_scores(self):
        self.assertFalse(evaluate_rule(
            "AND",
            required_keyword_ids=[1, 2],
            exclude_keyword_ids=[],
            paper_keyword_scores={1: 8.0},
        ))
        self.assertTrue(evaluate_rule(
            "AND",
            required_keyword_ids=[1, 2],
            exclude_keyword_ids=[],
            paper_keyword_scores={1: 1.0, 2: 0.5},
        ))

    def test_not_rule_matches_required_and_rejects_excluded_keywords(self):
        self.assertTrue(evaluate_rule(
            "NOT",
            required_keyword_ids=[1],
            exclude_keyword_ids=[2],
            paper_keyword_scores={1: 8.0},
        ))
        self.assertFalse(evaluate_rule(
            "NOT",
            required_keyword_ids=[1],
            exclude_keyword_ids=[2],
            paper_keyword_scores={1: 8.0, 2: 0.5},
        ))
        self.assertTrue(evaluate_rule(
            "NOT",
            required_keyword_ids=[1],
            exclude_keyword_ids=[2],
            paper_keyword_scores={1: 0.5, 2: 0.0},
        ))


class EmailTopicReportTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    async def _seed(self):
        async with SessionLocal() as db:
            alloy = Keyword(word="alloy", enabled=True)
            fatigue = Keyword(word="fatigue", enabled=True)
            corrosion = Keyword(word="corrosion", enabled=True)
            papers = [
                Paper(title="Alloy only", url="https://example.test/alloy"),
                Paper(title="Alloy fatigue", url="https://example.test/fatigue"),
                Paper(title="Alloy corrosion", url="https://example.test/corrosion"),
            ]
            db.add_all([alloy, fatigue, corrosion, *papers])
            await db.commit()
            for item in [alloy, fatigue, corrosion, *papers]:
                await db.refresh(item)

            db.add_all([
                AnalysisResult(
                    paper_id=papers[0].id,
                    keyword_id=alloy.id,
                    relevance_score=8,
                    summary="alloy",
                    analyzed_at=datetime.now(timezone.utc),
                ),
                AnalysisResult(
                    paper_id=papers[1].id,
                    keyword_id=alloy.id,
                    relevance_score=8,
                    summary="alloy",
                    analyzed_at=datetime.now(timezone.utc),
                ),
                AnalysisResult(
                    paper_id=papers[1].id,
                    keyword_id=fatigue.id,
                    relevance_score=7,
                    summary="fatigue",
                    analyzed_at=datetime.now(timezone.utc),
                ),
                AnalysisResult(
                    paper_id=papers[2].id,
                    keyword_id=alloy.id,
                    relevance_score=8,
                    summary="alloy",
                    analyzed_at=datetime.now(timezone.utc),
                ),
                AnalysisResult(
                    paper_id=papers[2].id,
                    keyword_id=corrosion.id,
                    relevance_score=7,
                    summary="corrosion",
                    analyzed_at=datetime.now(timezone.utc),
                ),
            ])
            await db.commit()
            return {
                "alloy": alloy.id,
                "fatigue": fatigue.id,
                "corrosion": corrosion.id,
            }

    async def test_topic_report_filters_and_rule(self):
        ids = await self._seed()
        async with SessionLocal() as db:
            rule = EmailTopicRule(name="Alloy AND fatigue", rule_type="AND", workspace_id=1)
            rule.set_keyword_ids([ids["alloy"], ids["fatigue"]])
            db.add(rule)
            await db.commit()
            await db.refresh(rule)

            report = await create_report_from_recent_analyses(db, source="unit-test", topic_rule=rule, workspace_id=1)

            self.assertEqual(1, report.paper_count)
            items = (await db.execute(select_report_items(report.id))).scalars().all()
            self.assertEqual(["Alloy fatigue"], [item.title for item in items])

    async def test_topic_report_filters_not_rule(self):
        ids = await self._seed()
        async with SessionLocal() as db:
            rule = EmailTopicRule(name="Alloy NOT corrosion", rule_type="NOT", workspace_id=1)
            rule.set_keyword_ids([ids["alloy"]])
            rule.set_exclude_keyword_ids([ids["corrosion"]])
            db.add(rule)
            await db.commit()
            await db.refresh(rule)

            report = await create_report_from_recent_analyses(db, source="unit-test", topic_rule=rule, workspace_id=1)

            self.assertEqual(2, report.paper_count)
            items = (await db.execute(select_report_items(report.id))).scalars().all()
            self.assertEqual(["Alloy fatigue", "Alloy only"], sorted(item.title for item in items))

    async def test_create_and_send_recent_report_sends_one_delivery_per_enabled_topic_with_matches(self):
        ids = await self._seed()
        async with SessionLocal() as db:
            and_rule = EmailTopicRule(name="AND topic", rule_type="AND", workspace_id=1)
            and_rule.set_keyword_ids([ids["alloy"], ids["fatigue"]])
            missing_rule = EmailTopicRule(name="Missing topic", rule_type="AND", workspace_id=1)
            missing_rule.set_keyword_ids([ids["fatigue"], ids["corrosion"]])
            db.add_all([and_rule, missing_rule])
            await db.commit()

            async def fake_send_report_email(db, report_id):
                from app.models import EmailDelivery

                report = await db.get(__import__("app.models", fromlist=["Report"]).Report, report_id)
                delivery = EmailDelivery(
                    report_id=report_id,
                    workspace_id=report.workspace_id,
                    recipient="reader@example.test",
                    subject=report.title,
                    status="sent",
                    paper_count=report.paper_count,
                )
                db.add(delivery)
                await db.commit()
                await db.refresh(delivery)
                return delivery

            with patch("app.services.report_center.send_report_email", fake_send_report_email):
                result = await create_and_send_recent_report(db, source="unit-test", workspace_id=1)

            self.assertEqual(1, result["sent_count"])
            self.assertEqual(1, result["paper_count"])
            self.assertEqual(2, len(result["topic_reports"]))
            self.assertTrue(result["topic_reports"][0]["sent"])
            self.assertEqual(0, result["topic_reports"][1]["paper_count"])


def select_report_items(report_id: int):
    from sqlalchemy import select

    return select(ReportItem).where(ReportItem.report_id == report_id).order_by(ReportItem.title)


if __name__ == "__main__":
    unittest.main()
