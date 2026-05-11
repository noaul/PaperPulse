from pydantic import BaseModel, Field
from datetime import datetime
from typing import Any, Literal, Optional


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
    paper_abstract: Optional[str] = None
    paper_authors: Optional[str] = None
    paper_url: Optional[str] = None
    journal_name: Optional[str] = None
    keyword_word: Optional[str] = None
    class Config:
        from_attributes = True


# Settings
class AIConfig(BaseModel):
    api_base: str = "https://api.openai.com/v1"
    api_key: str = ""
    model: str = "gpt-4o-mini"
    reasoning_effort: Literal["none", "low", "medium", "high", "xhigh"] = "xhigh"
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


# Workflow executions
class WorkflowExecutionLogOut(BaseModel):
    id: int
    execution_id: int
    node_name: str
    level: str
    message: str
    data: dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime]


class WorkflowExecutionOut(BaseModel):
    id: int
    workflow_name: str
    status: str
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    duration_ms: Optional[int]
    summary: dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None


class WorkflowExecutionDetail(WorkflowExecutionOut):
    logs: list[WorkflowExecutionLogOut] = Field(default_factory=list)


# Reports
class ReportItemOut(BaseModel):
    id: int
    report_id: int
    paper_id: Optional[int]
    title: str
    authors: Optional[str]
    abstract: Optional[str]
    url: Optional[str]
    journal_name: Optional[str]
    relevance_score: float
    summary: Optional[str]
    keywords: list[str] = Field(default_factory=list)


class EmailDeliveryOut(BaseModel):
    id: int
    report_id: Optional[int]
    recipient: Optional[str]
    subject: Optional[str]
    status: str
    error_message: Optional[str]
    paper_count: int
    created_at: Optional[datetime]
    sent_at: Optional[datetime]


class ReportOut(BaseModel):
    id: int
    title: str
    source: Optional[str]
    status: str
    threshold: float
    paper_count: int
    max_relevance_score: float
    created_at: Optional[datetime]
    sent_at: Optional[datetime]


class ReportDetail(ReportOut):
    markdown: str
    html: str
    items: list[ReportItemOut] = Field(default_factory=list)
    deliveries: list[EmailDeliveryOut] = Field(default_factory=list)


class ReportCreate(BaseModel):
    threshold: float = 6.0
    source: str = "manual"
