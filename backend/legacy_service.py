# Legacy question assignments for backward compatibility
# This maintains the existing API structure while using PostgreSQL

from sqlalchemy.orm import Session
from models import User, Assignment, Question, Submission, StudentAnswer
from database import get_db
import json
import uuid
import datetime
from typing import List, Dict, Any

class LegacyQuestionAssignment:
    """
    Legacy compatibility layer for the existing question assignment system.
    Maps the old SQLite schema to PostgreSQL models.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def store_questions(self, questions_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Store questions in the new PostgreSQL schema"""
        try:
            stored_questions = []
            
            for question_data in questions_data:
                # Generate unique ID using timestamp and UUID
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                unique_id = f"{timestamp}_{str(uuid.uuid4())[:8]}"
                
                # Extract data from the question
                question_text = question_data.get("question", "")
                marks = question_data.get("marks", 0)
                topic_list = question_data.get("topic", [])
                evaluation_rubrics = question_data.get("rubrics", [])
                
                # For legacy compatibility, we'll store these as a special assignment
                # Create a temporary assignment if it doesn't exist
                assignment_title = f"Legacy-{'-'.join(topic_list) if topic_list else 'General'}"
                
                # Check if assignment exists
                assignment = self.db.query(Assignment).filter(
                    Assignment.title == assignment_title,
                    Assignment.teacher_id == "system"  # Use system as the teacher for legacy questions
                ).first()
                
                if not assignment:
                    # Create a system assignment for legacy questions
                    assignment = Assignment(
                        title=assignment_title,
                        description=f"Legacy questions for topics: {', '.join(topic_list)}",
                        teacher_id="system",
                        course_id="legacy",
                        total_marks=marks
                    )
                    self.db.add(assignment)
                    self.db.flush()  # Get the ID
                
                # Create the question
                question = Question(
                    assignment_id=assignment.id,
                    question_text=question_text,
                    answer="",  # Legacy system doesn't store answers
                    marks=marks,
                    question_order=1
                )
                self.db.add(question)
                
                stored_questions.append({
                    "id": unique_id,
                    "question": question_text,
                    "marks": marks,
                    "topic": topic_list,
                    "rubrics": evaluation_rubrics
                })
            
            self.db.commit()
            
            return {
                "status": "success",
                "message": f"Successfully stored {len(stored_questions)} questions",
                "stored_questions": stored_questions
            }
        
        except Exception as e:
            self.db.rollback()
            return {
                "status": "error",
                "message": f"Failed to store questions: {str(e)}"
            }
    
    def get_questions_by_topic(self, assignment_title: str) -> List[Dict[str, Any]]:
        """Get questions by assignment title (for legacy compatibility)"""
        try:
            # Extract topic from assignment title (format: "Assignment-{topic}")
            if assignment_title.startswith("Assignment-"):
                topic = assignment_title.replace("Assignment-", "")
                
                # Search for assignments with matching topic in title
                assignments = self.db.query(Assignment).filter(
                    Assignment.title.like(f"%{topic}%")
                ).all()
                
                questions = []
                for assignment in assignments:
                    for question in assignment.questions:
                        # Parse topic from assignment title for legacy format
                        topic_parts = assignment.title.replace("Legacy-", "").split("-")
                        questions.append({
                            'id': str(question.id),
                            'question': question.question_text,
                            'marks': question.marks,
                            'topic': topic_parts,
                            'rubrics': []  # Legacy system doesn't store detailed rubrics
                        })
                
                return questions
            
            return []
        
        except Exception as e:
            return []
    
    def get_all_questions(self) -> List[Dict[str, Any]]:
        """Get all stored questions"""
        try:
            questions = []
            
            # Get all questions from all assignments
            all_questions = self.db.query(Question).join(Assignment).all()
            
            for question in all_questions:
                # Parse topic from assignment title for legacy format
                topic_parts = question.assignment.title.replace("Legacy-", "").split("-")
                
                questions.append({
                    "id": str(question.id),
                    "question": question.question_text,
                    "marks": question.marks,
                    "topic": topic_parts,
                    "rubrics": [],  # Legacy system doesn't store detailed rubrics
                    "created_at": question.created_at.isoformat() if question.created_at else None
                })
            
            return questions
        
        except Exception as e:
            return []
