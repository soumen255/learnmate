from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pathlib import Path
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional
import os

# Load .env from project root before importing ai_engine
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)

from backend.ai_engine import generate_tutoring_response, generate_quiz

app = FastAPI(
    title="LearnMate AI Tutoring API",
    description="AI-powered tutoring and quiz generation using FastAPI and Groq.",
    version="1.0.0"
)

# Allow Streamlit to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Models ─────────────────────────────────────────────────────────────────────

class TutorRequest(BaseModel):
    subject: str = Field(..., description="Academic subject")
    level: str = Field(..., description="Learning level")
    question: str = Field(..., description="User's question")
    learning_style: str = Field("Text-based", description="Preferred learning style")
    background: str = Field("Unknown", description="Background knowledge level")
    language: str = Field("English", description="Preferred response language")


class QuizRequest(BaseModel):
    subject: str = Field(..., description="Academic subject")
    level: str = Field(..., description="Learning level")
    num_questions: int = Field(5, ge=1, le=10, description="Number of questions")
    reveal_format: Optional[bool] = Field(True, description="Format with hidden answers")


class TutorResponse(BaseModel):
    response: str


class QuizResponse(BaseModel):
    quiz: List[Dict[str, Any]]
    formatted_quiz: Optional[str] = None


# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.post("/tutor", response_model=TutorResponse)
async def tutor(request: TutorRequest):
    """Generate a personalised tutoring explanation."""
    try:
        explanation = generate_tutoring_response(
            request.subject,
            request.level,
            request.question,
            request.learning_style,
            request.background,
            request.language
        )
        return TutorResponse(response=explanation)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/quiz", response_model=QuizResponse)
async def generate_quiz_api(data: QuizRequest):
    """Generate a multiple-choice quiz."""
    try:
        result = generate_quiz(
            data.subject,
            data.level,
            data.num_questions,
            reveal_answer=data.reveal_format
        )
        if data.reveal_format:
            return {"quiz": result["quiz_data"], "formatted_quiz": result["formatted_quiz"]}
        return {"quiz": result["quiz_data"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/quiz-html/{subject}/{level}/{num_questions}", response_class=HTMLResponse)
async def generate_quiz_html(subject: str, level: str, num_questions: int = 5):
    """Return a formatted HTML quiz page."""
    try:
        result = generate_quiz(subject, level, num_questions, reveal_answer=True)
        return result["formatted_quiz"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    return {"status": "healthy"}