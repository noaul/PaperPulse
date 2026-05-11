import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


TEST_DIR = tempfile.TemporaryDirectory()
os.environ["DB_PATH"] = str(Path(TEST_DIR.name) / "paperpulse-email-test.db")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.email_sender import build_paper_url, open_smtp_connection


class EmailSenderTest(unittest.TestCase):
    def test_build_paper_url_prefers_original_url_without_doi(self):
        self.assertEqual("https://example.test/paper", build_paper_url("https://example.test/paper", None))

    def test_build_paper_url_falls_back_to_doi(self):
        self.assertEqual("https://doi.org/10.1000/example", build_paper_url("", "10.1000/example"))

    def test_open_smtp_connection_uses_ssl_for_465(self):
        with patch("app.services.email_sender.smtplib.SMTP_SSL") as smtp_ssl:
            open_smtp_connection({"smtp_server": "smtp.example.test", "smtp_port": 465})

        smtp_ssl.assert_called_once_with("smtp.example.test", 465, timeout=20)
