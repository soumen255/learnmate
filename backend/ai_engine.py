from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from pathlib import Path
from dotenv import load_dotenv
import os
import json
import re
import logging

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ── Load .env from project root ────────────────────────────────────────────────
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise EnvironmentError(
        f"GROQ_API_KEY not found. Make sure .env exists at: {env_path}"
    )

logger.info(f"GROQ_API_KEY loaded successfully from {env_path}")


# ── LLM initialisation ─────────────────────────────────────────────────────────
def get_llm():
    return ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=0.7,
        groq_api_key=GROQ_API_KEY
    )


# ── Tutoring ───────────────────────────────────────────────────────────────────
def generate_tutoring_response(subject, level, question, learning_style, background, language):
    """Generate a personalised tutoring response."""
    try:
        llm = get_llm()
        prompt = _create_tutoring_prompt(subject, level, question, learning_style, background, language)
        logger.info(f"Generating tutoring — subject: {subject}, level: {level}")
        response = llm.invoke([HumanMessage(content=prompt)])
    
        return _format_tutoring_response(response.content, learning_style)
    except Exception as e:
        logger.error(f"Error generating tutoring response: {e}")
        raise Exception(f"Failed to generate tutoring response: {e}")


def _create_tutoring_prompt(subject, level, question, learning_style, background, language):
    return f"""You are an expert tutor in {subject} at the {level} level.

STUDENT PROFILE:
- Background Knowledge: {background}
- Learning style preference: {learning_style}
- Language preference: {language}

QUESTION:
{question}

INSTRUCTIONS:
1. Provide a clear, educational explanation that directly addresses the question.
2. Tailor your explanation to a {background} student at {level} level.
3. Use {language} as the primary language.
4. Format your response with appropriate markdown for readability.

LEARNING STYLE ADAPTATIONS:
- For visual learners: Include descriptions of visual concepts, diagrams, or mental models.
- For text-based learners: Provide clear, structured explanations with defined concepts.
- For hands-on learners: Include practical examples, exercises, or real-world applications.

Your explanation should be educational, accurate, and engaging.
"""


def _format_tutoring_response(content, learning_style):
    if learning_style.lower() == "visual":
        return content + "\n\n*Note: Visualize these concepts as you read for better retention.*"
    elif learning_style.lower() == "hands-on":
        return content + "\n\n*Tip: Try working through the examples yourself to reinforce your learning.*"
    return content


# ── Quiz generation ────────────────────────────────────────────────────────────
def _create_quiz_prompt(subject, level, num_questions):
    return f"""Create a {level}-level quiz on {subject} with exactly {num_questions} questions.
Each question is multiple-choice with exactly 4 options and one correct answer.

Return ONLY a valid JSON array — no markdown, no extra text, nothing outside the array.

[
    {{
        "question": "Question text here",
        "options": ["Option A text", "Option B text", "Option C text", "Option D text"],
        "correct_answer": "Option A text",
        "explanation": "Brief explanation of why this is correct."
    }}
]

Rules:
- "correct_answer" must be the exact full text of one of the four options.
- Every question must have exactly 4 options in the "options" list.
- Do NOT include ```json or any other markdown formatting.
"""


def _create_fallback_quiz(subject, num_questions):
    logger.warning(f"Using fallback quiz for {subject}.")
    return [
        {
            "question": f"Sample question {i + 1} for {subject}",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "correct_answer": "Option A",
            "explanation": f"Sample explanation for question {i + 1}."
        }
        for i in range(num_questions)
    ]


def _validate_quiz_data(quiz_data):
    if not isinstance(quiz_data, list):
        raise ValueError("Quiz data must be a list.")
    for q in quiz_data:
        if not isinstance(q, dict):
            raise ValueError("Each item must be a dict.")
        if not all(k in q for k in ["question", "options", "correct_answer"]):
            raise ValueError("Missing required keys.")
        if not isinstance(q["options"], list) or len(q["options"]) != 4:
            raise ValueError("Each question must have exactly 4 options as a list.")


def _parse_quiz_response(response_content, subject, num_questions):
    try:
        cleaned = response_content.strip()
        # Strip markdown fences
        cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
        cleaned = re.sub(r'\s*```$', '', cleaned)
        cleaned = cleaned.strip()

        # Extract JSON array
        json_match = re.search(r'\[\s*\{.*\}\s*\]', cleaned, re.DOTALL)
        if json_match:
            cleaned = json_match.group(0)

        quiz_data = json.loads(cleaned)
        _validate_quiz_data(quiz_data)

        if len(quiz_data) > num_questions:
            quiz_data = quiz_data[:num_questions]

        for q in quiz_data:
            if "explanation" not in q:
                q["explanation"] = f"The correct answer is: {q['correct_answer']}."

        return quiz_data

    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Quiz parse error: {e}\nRaw:\n{response_content}")
        return _create_fallback_quiz(subject, num_questions)


def generate_quiz(subject, level, num_questions=5, reveal_answer=True):
    """Generate a multiple-choice quiz."""
    try:
        llm = get_llm()
        prompt = _create_quiz_prompt(subject, level, num_questions)
        logger.info(f"Generating quiz — subject: {subject}, level: {level}, questions: {num_questions}")
        response = llm.invoke([HumanMessage(content=prompt)])
        quiz_data = _parse_quiz_response(response.content, subject, num_questions)

        if reveal_answer:
            return {"quiz_data": quiz_data, "formatted_quiz": _format_quiz_with_reveal(quiz_data)}
        return {"quiz_data": quiz_data}

    except Exception as e:
        logger.error(f"Error generating quiz: {e}")
        raise Exception(f"Failed to generate quiz: {e}")


def _format_quiz_with_reveal(quiz_data):
    """Return a self-contained HTML quiz page."""
    html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: Arial, sans-serif; color: white; background-color: #121212; margin: 0; padding: 0; }
        .quiz-container { max-width: 800px; margin: 0 auto; padding: 20px; }
        .question { margin-bottom: 15px; padding: 20px; border: 1px solid #444; border-radius: 10px; background-color: #1e1e2f; }
        .question h3 { margin-top: 0; color: #90caf9; }
        .options { margin-left: 10px; }
        .option { margin: 10px 0; padding: 12px; border: 1px solid #555; border-radius: 6px; cursor: pointer; background-color: #2d2d44; transition: background-color 0.2s; }
        .option:hover { background-color: #3a3a5a; }
        .reveal-btn { background-color: #90caf9; color: #121212; border: none; padding: 8px 12px; border-radius: 4px; cursor: pointer; margin-top: 10px; font-weight: bold; transition: background-color 0.2s; }
        .reveal-btn:hover { background-color: #64b5f6; }
        .answer-section { margin-top: 20px; border: 2px solid #ffeb3b; border-radius: 10px; overflow: hidden; display: none; }
        .answer-header { background-color: #ffeb3b; color: #121212; padding: 10px; font-weight: bold; font-size: 18px; text-align: center; }
        .answer-content { padding: 15px; background-color: #fffde7; }
        .correct-answer { font-size: 16px; font-weight: bold; color: #388e3c; margin-bottom: 15px; }
        .explanation { color: #555; font-size: 14px; line-height: 1.5; }
        .selected-correct { background-color: #1b5e20 !important; border-color: #4caf50 !important; }
        .selected-incorrect { background-color: #b71c1c !important; border-color: #f44336 !important; }
    </style>
</head>
<body>
<div class="quiz-container">
    <h2 style="color:#2196f3;text-align:center;margin-bottom:30px;">Quiz</h2>
"""

    option_letters = ["A", "B", "C", "D"]

    for i, question in enumerate(quiz_data, 1):
        options = question["options"]
        correct_answer = question["correct_answer"]
        correct_index = options.index(correct_answer) if correct_answer in options else 0

        html += f"""
    <div class="question" id="question-{i}">
        <h3>Question {i}</h3>
        <p>{question['question']}</p>
        <div class="options">
"""
        for j, option in enumerate(options):
            html += f"""
            <div class="option" id="option-{i}-{j}"
                 onclick="selectOption({i}, {j}, {str(j == correct_index).lower()})">
                <strong>{option_letters[j]}.</strong> {option}
            </div>
"""
        html += f"""
        </div>
        <button class="reveal-btn" onclick="revealAnswer({i})">SHOW Answer</button>
        <div class="answer-section" id="answer-{i}">
            <div class="answer-header">CORRECT ANSWER</div>
            <div class="answer-content">
                <div class="correct-answer">{option_letters[correct_index]}. {correct_answer}</div>
                <div class="explanation">{question.get('explanation', '')}</div>
            </div>
        </div>
    </div>
"""

    html += """
</div>
<script>
    function selectOption(questionNum, optionNum, isCorrect) {
        var questionEl = document.getElementById('question-' + questionNum);
        var options = questionEl.querySelectorAll('.option');
        options.forEach(function(o) { o.className = 'option'; });
        var sel = document.getElementById('option-' + questionNum + '-' + optionNum);
        sel.className = isCorrect ? 'option selected-correct' : 'option selected-incorrect';
        if (!isCorrect) { revealAnswer(questionNum); }
    }

    function revealAnswer(questionNum) {
        var ans = document.getElementById('answer-' + questionNum);
        ans.style.display = 'block';
        setTimeout(function() {
            ans.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }, 100);
        ans.animate([
            { transform: 'scale(1)',    boxShadow: '0 0 0 rgba(255,235,59,0)' },
            { transform: 'scale(1.03)', boxShadow: '0 0 20px rgba(255,235,59,0.7)' },
            { transform: 'scale(1)',    boxShadow: '0 0 10px rgba(255,235,59,0.3)' }
        ], { duration: 1000, iterations: 1 });
    }
</script>
</body>
</html>
"""
    return html