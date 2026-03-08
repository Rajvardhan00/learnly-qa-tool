from sqlalchemy import create_engine, Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./learnly.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    runs = relationship("QuestionnaireRun", back_populates="user")
    reference_docs = relationship("ReferenceDoc", back_populates="user")


class ReferenceDoc(Base):
    __tablename__ = "reference_docs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    chunks_json = Column(Text)  # JSON serialized chunks
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="reference_docs")


class QuestionnaireRun(Base):
    __tablename__ = "questionnaire_runs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String, nullable=False)
    status = Column(String, default="pending")  # pending, processing, done
    total_questions = Column(Integer, default=0)
    answered_count = Column(Integer, default=0)
    not_found_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="runs")
    qa_items = relationship("QAItem", back_populates="run", order_by="QAItem.question_number")


class QAItem(Base):
    __tablename__ = "qa_items"
    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("questionnaire_runs.id"), nullable=False)
    question_number = Column(Integer, nullable=False)
    question_text = Column(Text, nullable=False)
    answer = Column(Text)
    citations = Column(Text)       # JSON list of citation strings
    evidence_snippet = Column(Text)
    confidence_score = Column(Float, default=0.0)
    is_edited = Column(Boolean, default=False)
    not_found = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    run = relationship("QuestionnaireRun", back_populates="qa_items")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    Base.metadata.create_all(bind=engine)
