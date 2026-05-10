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


class Setting(Base):
    __tablename__ = "settings"
    key = Column(String(255), primary_key=True)
    value = Column(Text, default="{}")
