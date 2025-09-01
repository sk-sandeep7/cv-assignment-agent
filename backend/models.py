from sqlalchemy import Column, Integer, String, Text, DateTime, Float
from sqlalchemy.sql import func
from database import Base

class QuestionAssignment(Base):
    __tablename__ = "questions"
    
    question_id = Column(String, primary_key=True)  # Unique question ID
    user_id = Column(String, nullable=False)  # User who created the question
    question = Column(Text, nullable=False)  # The question text
    marks = Column(Float, nullable=False)  # Marks for the question
    evaluation_metrics = Column(Text, nullable=False)  # Stored as JSON string
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
