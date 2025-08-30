from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3

from generate_openai import generate_questions_with_openai, generate_custom_question_with_openai
from evaluation_openai import generate_evaluation_rubrics_with_openai

app = FastAPI()

# Allow CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Local development
        "http://localhost:3000",  # Alternative local port
        "https://*.vercel.app",   # Vercel domains
        "https://*.onrender.com", # Render domains (if you deploy frontend there too)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# SQLite setup
conn = sqlite3.connect('assignments.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS assignments (id INTEGER PRIMARY KEY, question TEXT)''')
conn.commit()

class QuestionRequest(BaseModel):
    question: str

class CriteriaRequest(BaseModel):
    question: str

class TaskRequest(BaseModel):
    question: str
    criteria: list

class RegenerateRequest(BaseModel):
    topic: list

class CustomQuestionRequest(BaseModel):
    user_input: str
    index: int

class EvaluationRequest(BaseModel):
    question: str
    marks: int

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.post("/api/generate-questions")
async def generate_questions(request: Request):
    data = await request.json()
    user_topics = data.get("topic", [])
    num_questions = int(data.get("num_questions", 3))

    get_few_shots = generate_questions_with_openai(user_topics, num_questions)

    # Enforce the number of questions
    if len(get_few_shots) > num_questions:
        get_few_shots = get_few_shots[:num_questions]
        
    questions = [
        {"question": q["question"], "marks": q.get("marks", 7)} for q in get_few_shots
    ]
    # Save to DB for demo
    for q in questions:
        c.execute("INSERT INTO assignments (question) VALUES (?)", (q["question"],))
    conn.commit()
    return {"questions": questions}

@app.post("/api/get-evaluation-criteria")
def get_criteria(req: CriteriaRequest):
    # Example: return static criteria
    criteria = [
        "Clarity and accuracy of explanation.",
        "Depth of understanding demonstrated.",
        "Use of relevant examples."
    ]
    return {"criteria": criteria}

@app.post("/api/execute-task")
def execute_task(req: TaskRequest):
    # Example: just return success
    return {"status": "success", "message": "Task completed successfully."}


@app.post("/api/generate-evaluation-rubrics")
async def generate_evaluation_rubrics(req: EvaluationRequest):
    question_with_marks = f"{req.question} ({req.marks} marks)"
    rubrics = generate_evaluation_rubrics_with_openai(question_with_marks)
    if rubrics:
        return rubrics
    return {}


@app.post("/api/generate-custom-question")
async def generate_custom_question(req: CustomQuestionRequest):
    user_input = req.user_input
    new_question_data = generate_custom_question_with_openai(user_input)
    if new_question_data:
        return new_question_data
    return {}


@app.post("/api/regenerate-question")
async def regenerate_question(request: Request):
    data = await request.json()
    user_topics = data.get("topic", [])
    get_few_shots = generate_questions_with_openai(user_topics, 1)
    if get_few_shots:
        new_question = {
            "question": get_few_shots[0]["question"],
            "marks": get_few_shots[0].get("marks", 7)
        }
        return new_question
    return {}
