import json
import asyncio
import os
import sys
import tempfile
import unittest
from pathlib import Path


TEST_DIR = tempfile.TemporaryDirectory()
os.environ["DB_PATH"] = str(Path(TEST_DIR.name) / "paperpulse-test.db")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.database import Base, engine, SessionLocal
from app.models import AnalysisResult, Keyword, Paper, Setting, WorkflowExecution, WorkflowExecutionLog
from app.routers.executions import set_execution_control
from app.services import ai_analyzer
from app.services.ai_analyzer import analyze_new_papers
from app.workflows.context import WorkflowCancelled, WorkflowContext
from app.workflows.engine import WorkflowEngine
from app.workflows.nodes import ai_analyze as ai_analyze_node_module
from app.workflows.nodes import email_report as email_report_node_module
from app.workflows.nodes.ai_analyze import AiAnalyzeNode
from app.workflows.nodes.base import WorkflowNode
from app.workflows.nodes.email_report import EmailReportNode


class SummaryNode(WorkflowNode):
    def __init__(self):
        super().__init__("summary-node")

    async def run(self, context):
        context.summary["count"] = 3
        await context.log("info", "summary updated", {"count": 3})


class FailingNode(WorkflowNode):
    def __init__(self):
        super().__init__("failing-node")

    async def run(self, context):
        raise RuntimeError("node exploded")


class ProgressNode(WorkflowNode):
    def __init__(self):
        super().__init__("progress-node")

    async def run(self, context):
        await context.update_summary(
            analysis_total=5,
            analysis_analyzed=2,
            analysis_related=1,
        )


class WorkflowEngineTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    async def test_successful_run_persists_execution_summary_and_logs(self):
        async with SessionLocal() as db:
            execution = await WorkflowEngine(db).run("unit-success", [SummaryNode()])

            self.assertEqual("success", execution.status)
            self.assertEqual({"count": 3}, json.loads(execution.summary_json))
            self.assertIsNotNone(execution.finished_at)
            self.assertIsNotNone(execution.duration_ms)

            result = await db.execute(
                select(WorkflowExecutionLog).where(WorkflowExecutionLog.execution_id == execution.id)
            )
            logs = result.scalars().all()

            self.assertGreaterEqual(len(logs), 3)
            self.assertIn("summary updated", [log.message for log in logs])

    async def test_failed_run_marks_execution_failed_and_records_error_log(self):
        async with SessionLocal() as db:
            execution = await WorkflowEngine(db).run("unit-failure", [FailingNode()])

            self.assertEqual("failed", execution.status)
            self.assertIn("node exploded", execution.error_message)

            result = await db.execute(
                select(WorkflowExecutionLog).where(WorkflowExecutionLog.execution_id == execution.id)
            )
            logs = result.scalars().all()

            self.assertTrue(any(log.level == "error" and "node exploded" in log.message for log in logs))

            persisted = await db.get(WorkflowExecution, execution.id)
            self.assertEqual("failed", persisted.status)

    async def test_node_can_persist_progress_before_workflow_finishes(self):
        async with SessionLocal() as db:
            execution = await WorkflowEngine(db).run("unit-progress", [ProgressNode()])

            self.assertEqual("success", execution.status)
            self.assertEqual(5, execution.summary_dict["analysis_total"])
            self.assertEqual(2, execution.summary_dict["analysis_analyzed"])
            self.assertEqual(1, execution.summary_dict["analysis_related"])

    async def test_analyze_new_papers_limits_progress_total_to_target_paper_ids(self):
        original_request = ai_analyzer.request_chat_completion

        async def fake_request_chat_completion(config, messages, max_tokens=500):
            return '{"relevance_score": 7, "matched_keywords": ["battery"], "summary": "相关"}'

        ai_analyzer.request_chat_completion = fake_request_chat_completion
        try:
            async with SessionLocal() as db:
                db.add(Setting(
                    key="ai_config",
                    value=json.dumps({"enabled": True, "api_key": "test-key", "api_base": "http://ai.test"}),
                ))
                db.add(Keyword(word="battery", enabled=True))
                papers = [
                    Paper(title="New paper A", url="https://example.com/a"),
                    Paper(title="New paper B", url="https://example.com/b"),
                    Paper(title="Old pending paper", url="https://example.com/c"),
                ]
                db.add_all(papers)
                await db.commit()
                for paper in papers:
                    await db.refresh(paper)

                progress_events = []

                async def on_progress(progress):
                    progress_events.append(progress)

                results = await analyze_new_papers(
                    db,
                    progress_callback=on_progress,
                    paper_ids=[papers[0].id, papers[1].id],
                    raise_errors=True,
                )

                self.assertEqual(2, len(results))
                self.assertEqual(2, progress_events[0]["analysis_total"])
                self.assertEqual(2, progress_events[-1]["analysis_analyzed"])

                analyzed_paper_ids = {result.paper_id for result in results}
                self.assertEqual({papers[0].id, papers[1].id}, analyzed_paper_ids)
        finally:
            ai_analyzer.request_chat_completion = original_request

    async def test_analyze_new_papers_without_targets_uses_latest_fetch_batch_only(self):
        original_request = ai_analyzer.request_chat_completion

        async def fake_request_chat_completion(config, messages, max_tokens=500):
            return '{"relevance_score": 7, "matched_keywords": ["battery"], "summary": "相关"}'

        ai_analyzer.request_chat_completion = fake_request_chat_completion
        try:
            async with SessionLocal() as db:
                db.add(Setting(
                    key="ai_config",
                    value=json.dumps({"enabled": True, "api_key": "test-key", "api_base": "http://ai.test"}),
                ))
                db.add(Keyword(word="battery", enabled=True))
                papers = [
                    Paper(title="Latest pending paper", url="https://example.com/latest-pending"),
                    Paper(title="Latest already analyzed paper", url="https://example.com/latest-analyzed"),
                    Paper(title="Older pending paper", url="https://example.com/older-pending"),
                ]
                db.add_all(papers)
                await db.commit()
                for paper in papers:
                    await db.refresh(paper)

                keyword = (await db.execute(select(Keyword).where(Keyword.word == "battery"))).scalar_one()
                db.add(AnalysisResult(
                    paper_id=papers[1].id,
                    keyword_id=keyword.id,
                    relevance_score=8,
                    summary="已分析",
                ))
                db.add(Setting(
                    key="latest_fetched_paper_ids",
                    value=json.dumps([papers[0].id, papers[1].id]),
                ))
                await db.commit()

                progress_events = []

                async def on_progress(progress):
                    progress_events.append(progress)

                results = await analyze_new_papers(
                    db,
                    progress_callback=on_progress,
                    raise_errors=True,
                )

                self.assertEqual(1, len(results))
                self.assertEqual(1, progress_events[0]["analysis_total"])
                self.assertEqual(1, progress_events[-1]["analysis_analyzed"])
                self.assertEqual(papers[0].id, results[0].paper_id)
        finally:
            ai_analyzer.request_chat_completion = original_request

    async def test_ai_analyze_node_passes_fetched_paper_ids_to_analyzer(self):
        original_analyze = ai_analyze_node_module.analyze_new_papers
        captured = {}

        async def fake_analyze_new_papers(
            db,
            progress_callback=None,
            control_callback=None,
            *,
            raise_errors=False,
            paper_ids=None,
        ):
            captured["paper_ids"] = paper_ids
            if progress_callback:
                await progress_callback({
                    "analysis_total": len(paper_ids or []),
                    "analysis_analyzed": 0,
                    "analysis_related": 0,
                    "analysis_results": 0,
                })
            return []

        ai_analyze_node_module.analyze_new_papers = fake_analyze_new_papers
        try:
            async with SessionLocal() as db:
                execution = WorkflowExecution(workflow_name="unit-ai-node", status="running")
                db.add(execution)
                await db.commit()
                await db.refresh(execution)

                context = WorkflowContext(db, execution)
                context.state["fetched_paper_ids"] = [10, 11, 12]

                await AiAnalyzeNode().run(context)

                self.assertEqual([10, 11, 12], captured["paper_ids"])
                self.assertEqual(3, context.summary["analysis_total"])
        finally:
            ai_analyze_node_module.analyze_new_papers = original_analyze

    async def test_email_report_node_scopes_report_to_fetched_paper_ids(self):
        original_send = email_report_node_module.send_daily_report
        captured = {}

        async def fake_send_daily_report(
            db,
            threshold=6.0,
            *,
            paper_ids=None,
            analyzed_count=None,
            related_count=None,
        ):
            captured["threshold"] = threshold
            captured["paper_ids"] = paper_ids
            captured["analyzed_count"] = analyzed_count
            captured["related_count"] = related_count
            return {
                "report_id": 123,
                "sent": True,
                "skipped": False,
                "reason": "",
                "paper_count": 1,
                "delivery_id": 456,
            }

        email_report_node_module.send_daily_report = fake_send_daily_report
        try:
            async with SessionLocal() as db:
                db.add(Setting(
                    key="schedule_config",
                    value=json.dumps({"cron_hour": 6, "cron_minute": 0, "relevance_threshold": 6.5}),
                ))
                execution = WorkflowExecution(workflow_name="unit-email-node", status="running")
                db.add(execution)
                await db.commit()
                await db.refresh(execution)

                context = WorkflowContext(db, execution)
                context.state["fetched_paper_ids"] = [10, 11, 12]
                context.summary.update({"analysis_analyzed": 3, "analysis_related": 1})

                await EmailReportNode().run(context)

                self.assertEqual(6.5, captured["threshold"])
                self.assertEqual([10, 11, 12], captured["paper_ids"])
                self.assertEqual(3, captured["analyzed_count"])
                self.assertEqual(1, captured["related_count"])
                self.assertEqual(1, context.summary["email_paper_count"])
        finally:
            email_report_node_module.send_daily_report = original_send

    async def test_execution_control_pause_resume_and_cancel_updates_status_and_summary(self):
        async with SessionLocal() as db:
            execution = WorkflowExecution(workflow_name="unit-control", status="running")
            db.add(execution)
            await db.commit()
            await db.refresh(execution)

            paused = await set_execution_control(db, execution.id, "pause")
            self.assertEqual("paused", paused.status)
            self.assertEqual("pause_requested", paused.summary_dict["execution_control"])

            resumed = await set_execution_control(db, execution.id, "resume")
            self.assertEqual("running", resumed.status)
            self.assertEqual("running", resumed.summary_dict["execution_control"])

            cancelled = await set_execution_control(db, execution.id, "cancel")
            self.assertEqual("cancelled", cancelled.status)
            self.assertEqual("cancel_requested", cancelled.summary_dict["execution_control"])

    async def test_context_cancel_request_marks_execution_cancelled(self):
        async with SessionLocal() as db:
            execution = WorkflowExecution(
                workflow_name="unit-cancel",
                status="running",
                summary_json=json.dumps({"execution_control": "cancel_requested"}),
            )
            db.add(execution)
            await db.commit()
            await db.refresh(execution)

            context = WorkflowContext(db, execution)

            with self.assertRaises(WorkflowCancelled):
                await context.wait_if_paused_or_cancelled(poll_interval=0)

            await db.refresh(execution)
            self.assertEqual("cancelled", execution.status)
            self.assertEqual("cancelled", execution.summary_dict["execution_control"])

    async def test_context_pause_waits_until_resume(self):
        async with SessionLocal() as db:
            execution = WorkflowExecution(
                workflow_name="unit-pause",
                status="running",
                summary_json=json.dumps({"execution_control": "pause_requested"}),
            )
            db.add(execution)
            await db.commit()
            await db.refresh(execution)

            context = WorkflowContext(db, execution)

            async def resume_soon():
                await asyncio.sleep(0.03)
                async with SessionLocal() as resume_db:
                    await set_execution_control(resume_db, execution.id, "resume")

            resume_task = asyncio.create_task(resume_soon())
            await context.wait_if_paused_or_cancelled(poll_interval=0.01)
            await resume_task

            await db.refresh(execution)
            self.assertEqual("running", execution.status)
            self.assertEqual("running", execution.summary_dict["execution_control"])
