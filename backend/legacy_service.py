# Simple question storage service for PostgreSQL single table
from sqlalchemy.orm import Session
from models import QuestionAssignment
import json
import uuid
import datetime
from typing import List, Dict, Any

class QuestionService:
    """
    Simple service for storing and retrieving questions in a single PostgreSQL table.
    """
    
    def __init__(self, db: Session, user_id: str = "system"):
        self.db = db
        self.user_id = user_id
    
    def store_questions(self, questions_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Store questions in the PostgreSQL questions table"""
        try:
            stored_questions = []
            
            for question_data in questions_data:
                # Generate unique question ID using timestamp and UUID
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                question_id = f"{timestamp}_{str(uuid.uuid4())[:8]}"
                
                # Extract data from the question
                question_text = question_data.get("question", "")
                marks = float(question_data.get("marks", 0))
                topic_list = question_data.get("topic", [])
                evaluation_rubrics = question_data.get("rubrics", [])
                
                # Store evaluation metrics as JSON (including topic and rubrics)
                evaluation_metrics = {
                    "topic": topic_list,
                    "rubrics": evaluation_rubrics
                }
                
                # Create the question record
                question_record = QuestionAssignment(
                    question_id=question_id,
                    user_id=self.user_id,
                    question=question_text,
                    marks=marks,
                    evaluation_metrics=json.dumps(evaluation_metrics)
                )
                self.db.add(question_record)
                
                stored_questions.append({
                    "id": question_id,
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
                
                # Search for questions with matching topic in evaluation_metrics
                questions = self.db.query(QuestionAssignment).all()
                
                matching_questions = []
                for question in questions:
                    try:
                        metrics = json.loads(question.evaluation_metrics)
                        topics = metrics.get("topic", [])
                        
                        # Check if any topic matches
                        if any(topic.lower() in t.lower() for t in topics):
                            matching_questions.append({
                                'id': question.question_id,
                                'question': question.question,
                                'marks': question.marks,
                                'topic': topics,
                                'rubrics': metrics.get("rubrics", [])
                            })
                    except json.JSONDecodeError:
                        continue
                
                return matching_questions
            
            return []
        
        except Exception as e:
            return []
    
    def get_all_questions(self) -> List[Dict[str, Any]]:
        """Get all stored questions"""
        try:
            questions = []
            
            # Get all questions from the table
            all_questions = self.db.query(QuestionAssignment).order_by(QuestionAssignment.created_at.desc()).all()
            
            for question in all_questions:
                try:
                    metrics = json.loads(question.evaluation_metrics)
                    questions.append({
                        "id": question.question_id,
                        "question": question.question,
                        "marks": question.marks,
                        "topic": metrics.get("topic", []),
                        "rubrics": metrics.get("rubrics", []),
                        "created_at": question.created_at.isoformat() if question.created_at else None
                    })
                except json.JSONDecodeError:
                    # Fallback for malformed JSON
                    questions.append({
                        "id": question.question_id,
                        "question": question.question,
                        "marks": question.marks,
                        "topic": [],
                        "rubrics": [],
                        "created_at": question.created_at.isoformat() if question.created_at else None
                    })
            
            return questions
        
        except Exception as e:
            return []
