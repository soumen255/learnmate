# frontend/app.py
import streamlit as st
import requests
import uuid
from streamlit.components.v1 import html

st.set_page_config(page_title="LearnMate", page_icon=":mortar_board:", layout="wide")
st.title("🎓 LearnMate: Your Personalized Learning Companion")

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    try:
        st.image("frontend/logo.png")
    except Exception:
        st.markdown("## 🎓 LearnMate")

    st.header("Learning Preferences")
    subject = st.selectbox(
        "Select Subject",
        ["Mathematics", "Physics", "Computer Science", "History", "Biology", "Programming"]
    )
    level = st.selectbox("Select Level", ["Beginner", "Intermediate", "Advanced"])
    learning_style = st.selectbox("Learning Style", ["Visual", "Text-based", "Hands-on"])
    language = st.selectbox("Preferred Language", ["English", "Spanish", "Hindi", "German", "French"])
    background = st.selectbox("Background Knowledge", ["Beginner", "Some Knowledge", "Experienced"])

# ── API endpoint ───────────────────────────────────────────────────────────────
API_ENDPOINT = "http://192.168.0.224:8000"

tab1, tab2 = st.tabs(["Ask a Question", "Generate Quiz"])

# ── Tab 1 – Tutoring ───────────────────────────────────────────────────────────
with tab1:
    st.header("Ask Your Question")
    question = st.text_area(
        "What are we learning today? 📚🔥",
        "Explain Newton's second law of motion with examples."
    )

    if st.button("Get Explanation"):
        with st.spinner("Generating Personalized Explanation..."):
            try:
                resp = requests.post(
                    f"{API_ENDPOINT}/tutor",
                    json={
                        "subject": subject,
                        "level": level,
                        "question": question,
                        "learning_style": learning_style,
                        "language": language,
                        "background": background,
                    },
                    timeout=60
                )
                resp.raise_for_status()
                data = resp.json()
                st.success("Here's your personalized explanation:")
                st.markdown(data["response"])

            except requests.exceptions.ConnectionError:
                st.error("❌ Could not connect to the backend server.")
                st.info(f"Make sure FastAPI is running at {API_ENDPOINT}")
            except requests.exceptions.HTTPError as e:
                st.error(f"❌ Server error {e.response.status_code}: {e.response.text}")
            except Exception as e:
                st.error(f"❌ Unexpected error: {str(e)}")

# ── Tab 2 – Quiz ───────────────────────────────────────────────────────────────
with tab2:
    st.header("Test Your Knowledge with a Quiz")
    col1, col2 = st.columns([2, 1])
    with col1:
        num_questions = st.slider("Number of Questions", 1, 10, 5)
    with col2:
        quiz_button = st.button("Generate Quiz", use_container_width=True)

    if quiz_button:
        with st.spinner("Generating Quiz..."):
            try:
                resp = requests.post(
                    f"{API_ENDPOINT}/quiz",
                    json={
                        "subject": subject,
                        "level": level,
                        "num_questions": num_questions,
                        "reveal_format": True,
                    },
                    timeout=60
                )
                resp.raise_for_status()
                data = resp.json()

                st.success("Here's your quiz:")

                if "formatted_quiz" in data and data["formatted_quiz"]:
                    html(data["formatted_quiz"], height=num_questions * 300, scrolling=True)
                else:
                    for i, q in enumerate(data["quiz"]):
                        with st.expander(f"Question {i + 1}: {q['question']}", expanded=True):
                            session_id = str(uuid.uuid4())
                            selected = st.radio(
                                "Select your answer:",
                                q["options"],
                                key=f"q_{session_id}"
                            )
                            if st.button("Check Answer", key=f"check_{session_id}"):
                                if selected == q["correct_answer"]:
                                    st.success(f"✅ Correct! {q.get('explanation', '')}")
                                else:
                                    st.error(f"❌ Incorrect. The correct answer is: {q['correct_answer']}")
                                    if "explanation" in q:
                                        st.info(q["explanation"])

            except requests.exceptions.ConnectionError:
                st.error("❌ Could not connect to the backend server.")
                st.info(f"Make sure FastAPI is running at {API_ENDPOINT}")
            except requests.exceptions.HTTPError as e:
                st.error(f"❌ Server error {e.response.status_code}: {e.response.text}")
            except Exception as e:
                st.error(f"❌ Unexpected error: {str(e)}")

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("Made with ❤️ by Team LearnMate")