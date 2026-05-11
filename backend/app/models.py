import json
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from .database import Base


class Feed(Base):
    __tablename__ = "feeds"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    url = Column(String(1024), nullable=False, unique=True)
    journal_name = Column(String(255))
    enabled = Column(Boolean, default=True)
    last_fetched = Column(DateTime)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    papers = relationship("Paper", back_populates="feed", cascade="all, delete-orphan")


class Paper(Base):
    __tablename__ = "papers"
    id = Column(Integer, primary_key=True, autoincrement=True)
    feed_id = Column(Integer, ForeignKey("feeds.id", ondelete="CASCADE"))
    title = Column(String(1024), nullable=False)
    authors = Column(Text)
    abstract = Column(Text)
    doi = Column(String(512), unique=True)
    url = Column(String(1024))
    published_at = Column(DateTime)
    fetched_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    category = Column(String(255))
    feed = relationship("Feed", back_populates="papers")
    analyses = relationship("AnalysisResult", back_populates="paper", cascade="all, delete-orphan")


class Keyword(Base):
    __tablename__ = "keywords"
    id = Column(Integer, primary_key=True, autoincrement=True)
    word = Column(String(255), nullable=False, unique=True)
    category = Column(String(255), default="default")
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    analyses = relationship("AnalysisResult", back_populates="keyword", cascade="all, delete-orphan")


class AnalysisResult(Base):
    __tablename__ = "analysis_results"
    id = Column(Integer, primary_key=True, autoincrement=True)
    paper_id = Column(Integer, ForeignKey("papers.id", ondelete="CASCADE"))
    keyword_id = Column(Integer, ForeignKey("keywords.id", ondelete="CASCADE"))
    relevance_score = Column(Float, default=0)
    summary = Column(Text)
    analyzed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    paper = relationship("Paper", back_populates="analyses")
    keyword = relationship("Keyword", back_populates="analyses")


class Report(Base):
    __tablename__ = "reports"
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(512), nullable=False)
    source = Column(String(255), default="manual")
    status = Column(String(50), default="ready", index=True)
    threshold = Column(Float, default=6.0)
    paper_count = Column(Integer, default=0)
    max_relevance_score = Column(Float, default=0)
    markdown = Column(Text, default="")
    html = Column(Text, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    sent_at = Column(DateTime)
    items = relationship("ReportItem", back_populates="report", cascade="all, delete-orphan")
    deliveries = relationship("EmailDelivery", back_populates="report", cascade="all, delete-orphan")


class ReportItem(Base):
    __tablename__ = "report_items"
    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(Integer, ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True)
    paper_id = Column(Integer, ForeignKey("papers.id", ondelete="SET NULL"), index=True)
    title = Column(String(1024), nullable=False)
    authors = Column(Text)
    abstract = Column(Text)
    url = Column(String(1024))
    journal_name = Column(String(255))
    relevance_score = Column(Float, default=0)
    summary = Column(Text)
    keywords_json = Column(Text, default="[]")
    report = relationship("Report", back_populates="items")
    paper = relationship("Paper")

    @property
    def keywords(self) -> list[str]:
        try:
            parsed = json.loads(self.keywords_json or "[]")
            return parsed if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            return []


class EmailDelivery(Base):
    __tablename__ = "email_deliveries"
    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(Integer, ForeignKey("reports.id", ondelete="SET NULL"), index=True)
    recipient = Column(String(512))
    subject = Column(String(512))
    status = Column(String(50), nullable=False, default="pending", index=True)
    error_message = Column(Text)
    paper_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    sent_at = Column(DateTime)
    report = relationship("Report", back_populates="deliveries")


class WeKnoraSync(Base):
    __tablename__ = "weknora_syncs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    paper_id = Column(Integer, ForeignKey("papers.id", ondelete="SET NULL"), index=True)
    report_id = Column(Integer, ForeignKey("reports.id", ondelete="SET NULL"), index=True)
    weknora_knowledge_id = Column(String(255), index=True)
    sync_type = Column(String(50), nullable=False, index=True)
    status = Column(String(50), nullable=False, default="pending", index=True)
    error_message = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    synced_at = Column(DateTime)
    paper = relationship("Paper")
    report = relationship("Report")


class WorkflowExecution(Base):
    __tablename__ = "workflow_executions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_name = Column(String(255), nullable=False, index=True)
    status = Column(String(50), nullable=False, default="pending", index=True)
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    finished_at = Column(DateTime)
    duration_ms = Column(Integer)
    summary_json = Column(Text, default="{}")
    error_message = Column(Text)
    logs = relationship("WorkflowExecutionLog", back_populates="execution", cascade="all, delete-orphan")

    @property
    def summary_dict(self) -> dict:
        try:
            return json.loads(self.summary_json or "{}")
        except json.JSONDecodeError:
            return {}


class WorkflowExecutionLog(Base):
    __tablename__ = "workflow_execution_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    execution_id = Column(Integer, ForeignKey("workflow_executions.id", ondelete="CASCADE"), nullable=False, index=True)
    node_name = Column(String(255), nullable=False)
    level = Column(String(50), nullable=False, default="info")
    message = Column(Text, nullable=False)
    data_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    execution = relationship("WorkflowExecution", back_populates="logs")

    @property
    def data_dict(self) -> dict:
        try:
            return json.loads(self.data_json or "{}")
        except json.JSONDecodeError:
            return {}


class Setting(Base):
    __tablename__ = "settings"
    key = Column(String(255), primary_key=True)
    value = Column(Text, default="{}")
