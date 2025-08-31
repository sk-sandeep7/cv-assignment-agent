import os
import json
import io
from typing import List, Dict, Any, Optional
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from openai import AzureOpenAI
from dotenv import load_dotenv
import PyPDF2

load_dotenv()

# Initialize Azure OpenAI Client
client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version=os.getenv("OPENAI_API_VERSION"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
)

deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

# Configuration check
print(f"OpenAI Endpoint: {os.getenv('AZURE_OPENAI_ENDPOINT')}")
print(f"OpenAI Deployment: {deployment_name}")
print(f"OpenAI API Key configured: {'Yes' if os.getenv('AZURE_OPENAI_API_KEY') else 'No'}")

async def extract_text_from_pdf(file_content: bytes) -> str:
    """Extract text content from PDF file."""
    try:
        pdf_file = io.BytesIO(file_content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        text_content = ""
        for page_num, page in enumerate(pdf_reader.pages):
            try:
                page_text = page.extract_text()
                text_content += f"\n--- Page {page_num + 1} ---\n{page_text}\n"
            except Exception as e:
                print(f"Error extracting text from page {page_num + 1}: {e}")
                continue
        
        return text_content.strip()
    except Exception as e:
        print(f"Error extracting PDF text: {e}")
        return ""

async def download_drive_file_content(drive_service, file_id: str) -> Optional[bytes]:
    """Download file content from Google Drive."""
    try:
        request = drive_service.files().get_media(fileId=file_id)
        file_content = request.execute()
        return file_content
    except HttpError as e:
        print(f"Error downloading file {file_id}: {e}")
        return None

async def generate_grade_with_openai(prompt: str) -> Optional[Dict]:
    """Generate grades using Azure OpenAI API."""
    try:
        response = client.chat.completions.create(
            model=deployment_name,
            messages=[
                {
                    "role": "system",
                    "content": """You are an expert academic evaluator. You must analyze student submissions carefully and provide fair, constructive grading.
                    
IMPORTANT: Always respond with valid JSON format exactly as specified. Do not include any text outside the JSON structure."""
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=2000,
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        return json.loads(content)
                    
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return None

async def evaluate_submission(
    submission_data: Dict,
    questions: List[Dict],
    drive_service,
    student_name: str = "Unknown Student"
) -> Optional[Dict]:
    """
    Evaluate a single student submission against the assignment questions and criteria.
    
    Args:
        submission_data: Google Classroom submission data
        questions: List of questions with evaluation criteria
        drive_service: Google Drive API service
        student_name: Name of the student
    
    Returns:
        Dictionary containing grading results or None if evaluation fails
    """
    try:
        # Extract submission content
        submission_text = ""
        attachment_texts = []
        
        # Process attachments
        if 'assignmentSubmission' in submission_data:
            assignment_sub = submission_data['assignmentSubmission']
            
            if 'attachments' in assignment_sub:
                for attachment in assignment_sub['attachments']:
                    if 'driveFile' in attachment:
                        drive_file = attachment['driveFile']
                        file_id = drive_file.get('id')
                        file_title = drive_file.get('title', 'Unknown File')
                        
                        print(f"Processing attachment: {file_title} (ID: {file_id})")
                        
                        # Download file content
                        file_content = await download_drive_file_content(drive_service, file_id)
                        
                        if file_content:
                            # Extract text from PDF
                            if file_title.lower().endswith('.pdf'):
                                pdf_text = await extract_text_from_pdf(file_content)
                                if pdf_text:
                                    attachment_texts.append(f"File: {file_title}\n{pdf_text}")
                                else:
                                    attachment_texts.append(f"File: {file_title}\n[Could not extract text from PDF]")
                            else:
                                attachment_texts.append(f"File: {file_title}\n[Non-PDF file - content not extracted]")
        
        # Combine all submission content
        if attachment_texts:
            submission_text = "\n\n".join(attachment_texts)
        else:
            submission_text = "[No readable content found in submission]"
        
        # Prepare evaluation prompt
        questions_text = ""
        total_possible_marks = 0
        
        for i, question in enumerate(questions, 1):
            question_text = question.get('question', '')
            marks = question.get('marks', 0)
            total_possible_marks += marks
            
            # Get evaluation criteria
            rubrics = question.get('rubrics', [])
            criteria_text = ""
            if rubrics:
                if isinstance(rubrics, list):
                    criteria_text = "\n".join([f"- {rubric}" for rubric in rubrics])
                else:
                    criteria_text = str(rubrics)
            else:
                criteria_text = "Standard academic evaluation criteria"
            
            questions_text += f"""
Question {i}: {question_text}
Maximum Marks: {marks}
Evaluation Criteria:
{criteria_text}

"""
        
        evaluation_prompt = f"""
You are grading a student's assignment submission. Please evaluate carefully and provide detailed feedback.

ASSIGNMENT QUESTIONS AND CRITERIA:
{questions_text}

STUDENT INFORMATION:
Student Name: {student_name}
Submission Status: {submission_data.get('state', 'Unknown')}

STUDENT SUBMISSION CONTENT:
{submission_text}

GRADING INSTRUCTIONS:
1. Read the student's submission carefully
2. Evaluate each question based on the provided criteria
3. Assign marks for each question (partial marks are allowed)
4. Provide constructive feedback for each question
5. Calculate total marks and assign an overall grade

RESPONSE FORMAT (Must be valid JSON):
{{
    "question_grades": [
        {{
            "question_number": 1,
            "marks_awarded": 0,
            "max_marks": {questions[0].get('marks', 0) if questions else 0},
            "feedback": "Detailed feedback for this question addressing strengths and areas for improvement"
        }}
    ],
    "total_marks": 0,
    "max_total_marks": {total_possible_marks},
    "overall_feedback": "Comprehensive summary of the student's performance across all questions",
    "grade_percentage": 0,
    "letter_grade": "A/B/C/D/F"
}}
"""
        
        # Generate grade using OpenAI
        grading_result = await generate_grade_with_openai(evaluation_prompt)
        
        if grading_result:
            # Add metadata
            grading_result['student_name'] = student_name
            grading_result['submission_id'] = submission_data.get('id')
            grading_result['evaluation_timestamp'] = submission_data.get('updateTime')
            
            print(f"Successfully graded submission for {student_name}: {grading_result['total_marks']}/{grading_result['max_total_marks']}")
            
        return grading_result
        
    except Exception as e:
        print(f"Error evaluating submission for {student_name}: {e}")
        return None

async def assign_grade_to_classroom(
    classroom_service,
    course_id: str,
    assignment_id: str,
    submission_id: str,
    assigned_grade: float,
    feedback: str = ""
) -> bool:
    """
    Assign grade to a student's submission in Google Classroom.
    
    Args:
        classroom_service: Google Classroom API service
        course_id: Course ID
        assignment_id: Assignment ID  
        submission_id: Submission ID
        assigned_grade: Grade to assign
        feedback: Optional feedback text
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Prepare the grade patch
        grade_patch = {
            'assignedGrade': assigned_grade
        }
        
        # Add feedback if provided
        if feedback:
            grade_patch['draftGrade'] = assigned_grade
        
        # Update the student submission with the grade
        result = classroom_service.courses().courseWork().studentSubmissions().patch(
            courseId=course_id,
            courseWorkId=assignment_id,
            id=submission_id,
            updateMask='assignedGrade,draftGrade',
            body=grade_patch
        ).execute()
        
        print(f"Successfully assigned grade {assigned_grade} to submission {submission_id}")
        return True
        
    except HttpError as error:
        print(f"Error assigning grade to submission {submission_id}: {error}")
        return False
    except Exception as e:
        print(f"Unexpected error assigning grade: {e}")
        return False
