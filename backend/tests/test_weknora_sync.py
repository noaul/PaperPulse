import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


TEST_DIR = tempfile.TemporaryDirectory()
os.environ["DB_PATH"] = str(Path(TEST_DIR.name) / "paperpulse-weknora-test.db")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.database import Base, engine, SessionLocal
from app.models import AnalysisResult, Keyword, Paper, Report, Setting, WeKnoraSync
from app.services.weknora_sync import (
    DEFAULT_WEKNORA_CONFIG,
    get_weknora_config,
    render_paper_markdown,
    sync_paper_to_weknora,
    sync_report_to_weknora,
)
from app.workflows.context import WorkflowContext
from app.workflows.nodes import weknora_sync as weknora_sync_node_module
from app.workflows.nodes.weknora_sync import WeKnoraSyncNode
from app.models import WorkflowExecution


class FakeWeKnoraClient:
    def __init__(self):
        self.created = []

    async def create_manual_knowledge(self, knowledge_base_id: str, title: str, content: str, channel: str = "api"):
        self.created.append({
            "knowledge_base_id": knowledge_base_id,
            "title": title,
            "content": content,
            "channel": channel,
        })
        return {"success": True, "data": {"id": f"wk-{len(self.created)}"}}


class WeKnoraSyncTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.seed_index = 0
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    async def save_config(self, **overrides):
        config = {**DEFAULT_WEKNORA_CONFIG, **overrides}
        async with SessionLocal() as db:
            db.add(Setting(key="weknora_config", value=json.dumps(config)))
            await db.commit()
        return config

    async def seed_analyzed_paper(self, score: float = 8.0) -> int:
        self.seed_index += 1
        suffix = self.seed_index
        async with SessionLocal() as db:
            paper = Paper(
                title=f"High entropy alloy fatigue {suffix}",
                authors="A. Researcher",
                abstract="A useful abstract about alloy fatigue.",
                doi=f"10.1234/example-{suffix}",
                url=f"https://example.test/paper-{suffix}?utm_source=rss",
                published_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
            )
            keyword = Keyword(word=f"alloy-{suffix}", enabled=True)
            db.add_all([paper, keyword])
            await db.commit()
            await db.refresh(paper)
            await db.refresh(keyword)
            db.add(AnalysisResult(
                paper_id=paper.id,
                keyword_id=keyword.id,
                relevance_score=score,
                summary="Highly relevant alloy paper",
                analyzed_at=datetime.now(timezone.utc),
            ))
            await db.commit()
            return paper.id

    async def test_get_weknora_config_returns_defaults_when_not_saved(self):
        async with SessionLocal() as db:
            config = await get_weknora_config(db)

        self.assertEqual(DEFAULT_WEKNORA_CONFIG, config)

    async def test_render_paper_markdown_includes_metadata_summary_and_abstract(self):
        paper = Paper(
            title="High entropy alloy fatigue",
            authors="A. Researcher",
            abstract="A useful abstract.",
            doi="10.1234/example",
            url="https://example.test/paper?utm_source=rss",
            published_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
        )
        analysis = AnalysisResult(
            relevance_score=8.5,
            summary="Highly relevant alloy paper",
        )
        keyword = Keyword(word="alloy")

        markdown = render_paper_markdown(paper, [(analysis, keyword, "Materials Today")])

        self.assertIn("# High entropy alloy fatigue", markdown)
        self.assertIn("- DOI: 10.1234/example", markdown)
        self.assertIn("- Journal: Materials Today", markdown)
        self.assertIn("- PaperPulse Score: 8.5", markdown)
        self.assertIn("- Matched Keywords: alloy", markdown)
        self.assertIn("Highly relevant alloy paper", markdown)
        self.assertIn("A useful abstract.", markdown)
        self.assertNotIn("utm_source", markdown)

    async def test_sync_report_to_weknora_creates_manual_knowledge_and_records_mapping(self):
        await self.save_config(
            enabled=True,
            base_url="http://weknora.test/api/v1",
            api_key="sk-test",
            knowledge_base_id="kb-paperpulse",
        )
        async with SessionLocal() as db:
            report = Report(title="PaperPulse Literature Report - 2026-05-11", markdown="# Report")
            db.add(report)
            await db.commit()
            await db.refresh(report)

            client = FakeWeKnoraClient()
            sync = await sync_report_to_weknora(db, report.id, client=client)

            self.assertEqual("success", sync.status)
            self.assertEqual("wk-1", sync.weknora_knowledge_id)
            self.assertEqual("report", sync.sync_type)
            self.assertEqual(report.id, sync.report_id)
            self.assertEqual("kb-paperpulse", client.created[0]["knowledge_base_id"])
            self.assertEqual(report.title, client.created[0]["title"])
            self.assertEqual("# Report", client.created[0]["content"])
            self.assertEqual("api", client.created[0]["channel"])

            persisted = await db.get(WeKnoraSync, sync.id)
            self.assertEqual("success", persisted.status)

    async def test_sync_report_to_weknora_reuses_successful_existing_sync(self):
        await self.save_config(enabled=True, base_url="http://weknora.test/api/v1", api_key="sk-test", knowledge_base_id="kb")
        async with SessionLocal() as db:
            report = Report(title="Existing report", markdown="# Existing")
            db.add(report)
            await db.commit()
            await db.refresh(report)
            db.add(WeKnoraSync(
                report_id=report.id,
                sync_type="report",
                status="success",
                weknora_knowledge_id="wk-existing",
            ))
            await db.commit()

            client = FakeWeKnoraClient()
            sync = await sync_report_to_weknora(db, report.id, client=client)

            self.assertEqual("wk-existing", sync.weknora_knowledge_id)
            self.assertEqual([], client.created)

    async def test_sync_paper_to_weknora_respects_min_score_and_records_mapping(self):
        await self.save_config(
            enabled=True,
            base_url="http://weknora.test/api/v1",
            api_key="sk-test",
            knowledge_base_id="kb-paperpulse",
            min_score_to_sync=7.0,
        )
        high_score_id = await self.seed_analyzed_paper(score=8.0)
        low_score_id = await self.seed_analyzed_paper(score=5.0)

        async with SessionLocal() as db:
            client = FakeWeKnoraClient()
            high_sync = await sync_paper_to_weknora(db, high_score_id, client=client)
            low_sync = await sync_paper_to_weknora(db, low_score_id, client=client)

            self.assertIsNotNone(high_sync)
            self.assertEqual("success", high_sync.status)
            self.assertEqual(high_score_id, high_sync.paper_id)
            self.assertEqual("wk-1", high_sync.weknora_knowledge_id)
            self.assertEqual("paper", high_sync.sync_type)
            self.assertIn("High entropy alloy fatigue", client.created[0]["content"])
            self.assertIsNone(low_sync)
            self.assertEqual(1, len(client.created))

    async def test_sync_paper_to_weknora_skips_when_disabled(self):
        await self.save_config(enabled=False, base_url="http://weknora.test/api/v1", api_key="sk-test", knowledge_base_id="kb")
        paper_id = await self.seed_analyzed_paper(score=8.0)

        async with SessionLocal() as db:
            client = FakeWeKnoraClient()
            sync = await sync_paper_to_weknora(db, paper_id, client=client)

            self.assertIsNone(sync)
            self.assertEqual([], client.created)

    async def test_weknora_sync_node_syncs_report_and_fetched_papers_into_summary(self):
        original_sync_report = weknora_sync_node_module.sync_report_to_weknora
        original_sync_papers = weknora_sync_node_module.sync_papers_to_weknora
        calls = {}

        async def fake_sync_report(db, report_id):
            calls["report_id"] = report_id
            return WeKnoraSync(report_id=report_id, sync_type="report", status="success", weknora_knowledge_id="wk-report")

        async def fake_sync_papers(db, paper_ids):
            calls["paper_ids"] = paper_ids
            return [
                WeKnoraSync(paper_id=paper_ids[0], sync_type="paper", status="success", weknora_knowledge_id="wk-paper")
            ]

        weknora_sync_node_module.sync_report_to_weknora = fake_sync_report
        weknora_sync_node_module.sync_papers_to_weknora = fake_sync_papers
        try:
            async with SessionLocal() as db:
                execution = WorkflowExecution(
                    workflow_name="unit-weknora-node",
                    status="running",
                    summary_json=json.dumps({"email_report_id": 42}),
                )
                db.add(execution)
                await db.commit()
                await db.refresh(execution)

                context = WorkflowContext(db, execution)
                context.summary.update(execution.summary_dict)
                context.state["fetched_paper_ids"] = [10, 11]

                await WeKnoraSyncNode().run(context)

                self.assertEqual(42, calls["report_id"])
                self.assertEqual([10, 11], calls["paper_ids"])
                self.assertEqual(1, context.summary["weknora_reports_synced"])
                self.assertEqual(1, context.summary["weknora_papers_synced"])
        finally:
            weknora_sync_node_module.sync_report_to_weknora = original_sync_report
            weknora_sync_node_module.sync_papers_to_weknora = original_sync_papers
