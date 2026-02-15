
import uuid
from sqlalchemy import Column, String, Integer, BigInteger, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from app.db.session import Base

class Run(Base):
    __tablename__ = "runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    keyword = Column(Text, nullable=False)
    hl = Column(String, default="id")
    gl = Column(String, default="ID")
    status = Column(String, default="queued") # queued, running, success, partial, failed
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    videos = relationship("Video", back_populates="run", cascade="all, delete-orphan")
    templates = relationship("Template", back_populates="run", cascade="all, delete-orphan")

class Video(Base):
    __tablename__ = "videos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.id"), nullable=False)
    
    source_type = Column(String, nullable=False) # search, people_also_watched, related_fallback
    rank = Column(Integer, nullable=False)
    title = Column(Text, nullable=False)
    channel_name = Column(Text, nullable=False)
    video_id = Column(Text, nullable=False)
    video_url = Column(Text, nullable=False)
    views_raw = Column(Text, nullable=False)
    views_num = Column(BigInteger, nullable=True)
    published_raw = Column(Text, nullable=True)
    duration_raw = Column(Text, nullable=True)
    collected_from = Column(String, nullable=False) # search, module, watch_page
    created_at = Column(DateTime, default=datetime.utcnow)

    run = relationship("Run", back_populates="videos")

class Template(Base):
    __tablename__ = "templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.id"), nullable=False)
    template_text = Column(Text, nullable=False)
    example_1 = Column(Text, nullable=True)
    example_2 = Column(Text, nullable=True)

    run = relationship("Run", back_populates="templates")
