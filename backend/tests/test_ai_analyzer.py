import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


TEST_DIR = tempfile.TemporaryDirectory()
os.environ["DB_PATH"] = str(Path(TEST_DIR.name) / "paperpulse-ai-test.db")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.ai_analyzer import (
    analyze_paper,
    build_ai_request,
    extract_response_text,
    request_chat_completion,
)
from app.database import Base, SessionLocal, engine
from app.models import Keyword, Paper


class AiAnalyzerTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    def test_build_ai_request_supports_full_responses_endpoint(self):
        url, payload = build_ai_request(
            {
                "api_base": "https://api.openai.com/v1/responses",
                "api_key": "test-key",
                "model": "gpt-4o-mini",
                "reasoning_effort": "xhigh",
            },
            [{"role": "user", "content": "Reply OK"}],
            max_tokens=8,
            temperature=0,
        )

        self.assertEqual("https://api.openai.com/v1/responses", url)
        self.assertEqual("gpt-4o-mini", payload["model"])
        self.assertEqual([{"role": "user", "content": "Reply OK"}], payload["input"])
        self.assertEqual(8, payload["max_output_tokens"])
        self.assertEqual({"effort": "xhigh"}, payload["reasoning"])
        self.assertNotIn("messages", payload)
        self.assertNotIn("max_tokens", payload)

    def test_extract_response_text_supports_responses_output_items(self):
        content = extract_response_text({
            "output": [
                {
                    "type": "message",
                    "content": [
                        {"type": "output_text", "text": "{\"ok\": true}"},
                    ],
                }
            ]
        })

        self.assertEqual('{"ok": true}', content)

    def test_build_ai_request_omits_reasoning_when_effort_is_none(self):
        _url, payload = build_ai_request(
            {
                "api_base": "https://api.openai.com/v1/responses",
                "api_key": "test-key",
                "model": "gpt-4o-mini",
                "reasoning_effort": "none",
            },
            [{"role": "user", "content": "Reply OK"}],
            max_tokens=8,
        )

        self.assertNotIn("reasoning", payload)

    async def test_request_chat_completion_posts_responses_payload_and_extracts_text(self):
        captured = {}

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "output": [
                        {
                            "type": "message",
                            "content": [
                                {"type": "output_text", "text": "OK"},
                            ],
                        }
                    ]
                }

        class FakeClient:
            def __init__(self, timeout):
                self.timeout = timeout

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return None

            async def post(self, url, headers, json):
                captured["url"] = url
                captured["headers"] = headers
                captured["json"] = json
                return FakeResponse()

        with patch("app.services.ai_analyzer.httpx.AsyncClient", FakeClient):
            text = await request_chat_completion(
                {
                    "api_base": "https://api.openai.com/v1/responses",
                    "api_key": "test-key",
                    "model": "gpt-4o-mini",
                },
                [{"role": "user", "content": "Reply OK"}],
                max_tokens=8,
            )

        self.assertEqual("OK", text)
        self.assertEqual("https://api.openai.com/v1/responses", captured["url"])
        self.assertEqual(8, captured["json"]["max_output_tokens"])
        self.assertEqual([{"role": "user", "content": "Reply OK"}], captured["json"]["input"])

    async def test_analyze_paper_only_persists_keywords_returned_as_matched(self):
        async def fake_request_chat_completion(config, messages, max_tokens=500):
            return '{"relevance_score": 8, "matched_keywords": ["alloy"], "summary": "Only alloy is relevant"}'

        with patch("app.services.ai_analyzer.request_chat_completion", fake_request_chat_completion):
            async with SessionLocal() as db:
                paper = Paper(title="Alloy fatigue paper", abstract="This paper studies alloys.")
                alloy = Keyword(word="alloy", enabled=True)
                fatigue = Keyword(word="fatigue", enabled=True)
                db.add_all([paper, alloy, fatigue])
                await db.commit()
                await db.refresh(paper)
                await db.refresh(alloy)
                await db.refresh(fatigue)

                results = await analyze_paper(
                    db,
                    paper,
                    [alloy, fatigue],
                    {"enabled": True, "api_key": "test-key", "api_base": "http://ai.test"},
                    raise_errors=True,
                )

                self.assertEqual(1, len(results))
                self.assertEqual(alloy.id, results[0].keyword_id)


if __name__ == "__main__":
    unittest.main()
