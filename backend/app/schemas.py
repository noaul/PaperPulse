from pydantic import BaseModel
from datetime import datetime
from typing import Optional


# Feed
class FeedCreate(BaseModel):
    name: str
    url: str
    journal_name: Optional[str] = None
    enabled: bool = True

class FeedUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    journal_name: Optional[str] = None
    enabled: Optional[bool] = None

class FeedOut(BaseModel):
    id: int
    name: str
    url: str
    journal_name: Optional[str]
    enabled: bool
    last_fetched: Optional[datetime]
    created_at: Optional[datetime]
    paper_count: int = 0
    class Config:
        from_attributes = True


# Paper
class PaperOut(BaseModel):
    id: int
    feed_id: Optional[int]
    title: str
    authors: Optional[str]
    abstract: Optional[str]
    doi: Optional[str]
    url: Optional[str]
    published_at: Optional[datetime]
    fetched_at: Optional[datetime]
    category: Optional[str]
    journal_name: Optional[str] = None
    relevance_score: Optional[float] = None
    analysis_summary: Optional[str] = None
    class Config:
        from_attributes = True


# Keyword
class KeywordCreate(BaseModel):
    word: str
    category: str = "default"
    enabled: bool = True

class KeywordUpdate(BaseModel):
    word: Optional[str] = None
    category: Optional[str] = None
    enabled: Optional[bool] = None

class KeywordOut(BaseModel):
    id: int
    word: str
    category: str
    enabled: bool
    created_at: Optional[datetime]
    class Config:
        from_attributes = True


# Analysis
class AnalysisOut(BaseModel):
    id: int
    paper_id: int
    keyword_id: int
    relevance_score: float
    summary: Optional[str]
    analyzed_at: Optional[datetime]
    paper_title: Optional[str] = None
    keyword_word: Optional[str] = None
    class Config:
        from_attributes = True


# Settings
class AIConfig(BaseModel):
    api_base: str = "https://api.openai.com/v1"
    api_key: str = ""
    model: str = "gpt-4o-mini"
    enabled: bool = True

class EmailConfig(BaseModel):
    smtp_server: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    sender_name: str = "PaperPulse"
    recipient: str = ""
    enabled: bool = False

class WebDAVConfig(BaseModel):
    url: str = ""
    username: str = ""
    password: str = ""
    remote_path: str = "/PaperPulse/"

class ScheduleConfig(BaseModel):
    cron_hour: int = 6
    cron_minute: int = 0
    relevance_threshold: float = 6.0


# Dashboard
class DashboardStats(BaseModel):
    total_feeds: int
    total_papers: int
    total_keywords: int = 0
    today_papers: int
    today_analyses: int
    high_relevance_today: int


class RecentPaperOut(BaseModel):
    id: int
    title: str
    journal: Optional[str] = None
    relevance_score: float = 0.0
    published_date: Optional[str] = None
