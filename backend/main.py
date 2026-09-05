from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from rag.query import search

import sqlite3
from datetime import datetime

app = FastAPI(title="Campus Helpdesk RAG Chatbot")


# -----------------------------
# CORS
# -----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------
# DATABASE
# -----------------------------
DB_NAME = "chatbot.db"


def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def create_database():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            answer TEXT,
            timestamp TEXT NOT NULL,
            feedback TEXT
        )
    """)

    conn.commit()
    conn.close()


create_database()


# -----------------------------
# HOME
# -----------------------------
@app.get("/")
def home():
    return {
        "message": "Campus Helpdesk RAG Backend is running!"
    }


# -----------------------------
# QUESTION MODEL
# -----------------------------
class Question(BaseModel):
    question: str


# -----------------------------
# ASK CHATBOT
# -----------------------------
@app.post("/ask")
def ask_question(data: Question):

    results = search(data.question)

    if not results:
        answer = "Sorry, I could not find relevant information."
    else:
        answer = "\n\n".join(results)

    # Save chat in database
    conn = get_db()

    conn.execute(
        """
        INSERT INTO chats (question, answer, timestamp)
        VALUES (?, ?, ?)
        """,
        (
            data.question,
            answer,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
    )

    conn.commit()
    conn.close()

    return {
        "answer": answer
    }


# -----------------------------
# DASHBOARD STATISTICS
# -----------------------------
@app.get("/dashboard/stats")
def dashboard_stats():

    conn = get_db()

    total_questions = conn.execute(
        "SELECT COUNT(*) FROM chats"
    ).fetchone()[0]

    total_feedback = conn.execute(
        "SELECT COUNT(*) FROM chats WHERE feedback IS NOT NULL"
    ).fetchone()[0]

    positive_feedback = conn.execute(
        "SELECT COUNT(*) FROM chats WHERE feedback = 'positive'"
    ).fetchone()[0]

    negative_feedback = conn.execute(
        "SELECT COUNT(*) FROM chats WHERE feedback = 'negative'"
    ).fetchone()[0]

    today_questions = conn.execute(
        """
        SELECT COUNT(*)
        FROM chats
        WHERE date(timestamp) = date('now', 'localtime')
        """
    ).fetchone()[0]

    conn.close()

    return {
        "total_questions": total_questions,
        "total_conversations": total_questions,
        "today_questions": today_questions,
        "feedback_count": total_feedback,
        "positive_feedback": positive_feedback,
        "negative_feedback": negative_feedback
    }


# -----------------------------
# RECENT QUESTIONS
# -----------------------------
@app.get("/dashboard/recent")
def recent_questions():

    conn = get_db()

    rows = conn.execute(
        """
        SELECT id, question, timestamp
        FROM chats
        ORDER BY id DESC
        LIMIT 10
        """
    ).fetchall()

    conn.close()

    return [
        {
            "id": row["id"],
            "question": row["question"],
            "timestamp": row["timestamp"]
        }
        for row in rows
    ]


# -----------------------------
# POPULAR QUESTIONS
# -----------------------------
@app.get("/dashboard/popular")
def popular_questions():

    conn = get_db()

    rows = conn.execute(
        """
        SELECT question, COUNT(*) AS count
        FROM chats
        GROUP BY question
        ORDER BY count DESC
        LIMIT 5
        """
    ).fetchall()

    conn.close()

    return [
        {
            "question": row["question"],
            "count": row["count"]
        }
        for row in rows
    ]


# -----------------------------
# QUESTIONS PER DAY
# -----------------------------
@app.get("/dashboard/daily")
def daily_questions():

    conn = get_db()

    rows = conn.execute(
        """
        SELECT date(timestamp) AS day, COUNT(*) AS count
        FROM chats
        GROUP BY date(timestamp)
        ORDER BY day DESC
        LIMIT 7
        """
    ).fetchall()

    conn.close()

    return [
        {
            "day": row["day"],
            "count": row["count"]
        }
        for row in rows
    ]


# -----------------------------
# FEEDBACK
# -----------------------------
class Feedback(BaseModel):
    chat_id: int
    feedback: str


@app.post("/dashboard/feedback")
def add_feedback(data: Feedback):

    if data.feedback not in ["positive", "negative"]:
        return {
            "success": False,
            "message": "Invalid feedback"
        }

    conn = get_db()

    conn.execute(
        """
        UPDATE chats
        SET feedback = ?
        WHERE id = ?
        """,
        (
            data.feedback,
            data.chat_id
        )
    )

    conn.commit()
    conn.close()

    return {
        "success": True
    }
