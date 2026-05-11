import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


TEST_DIR = tempfile.TemporaryDirectory()
os.environ["DB_PATH"] = str(Path(TEST_DIR.name) / "paperpulse-rss-test.db")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.rss_fetcher import clean_text, extract_abstract, normalize_paper_url


class RssFetcherTest(unittest.TestCase):
    def test_clean_text_strips_html_and_collapses_whitespace(self):
        self.assertEqual("Battery abstract text", clean_text("<p>Battery&nbsp; abstract\n text</p>"))

    def test_extract_abstract_reads_content_when_summary_missing(self):
        entry = SimpleNamespace(content=[{"value": "<div>Detailed abstract</div>"}])

        self.assertEqual("Detailed abstract", extract_abstract(entry))

    def test_normalize_paper_url_removes_sciencedirect_rss_tracking(self):
        url = "https://www.sciencedirect.com/science/article/pii/S1359645426004003?dgcid=rss_sd_all"

        self.assertEqual(
            "https://www.sciencedirect.com/science/article/pii/S1359645426004003",
            normalize_paper_url(url),
        )

    def test_normalize_paper_url_preserves_non_tracking_query_parameters(self):
        url = "https://example.com/article?id=42&utm_source=rss&utm_campaign=feed"

        self.assertEqual("https://example.com/article?id=42", normalize_paper_url(url))
