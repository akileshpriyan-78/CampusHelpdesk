from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from rag.query import search

import sqlite3
import hashlib
import hmac
import time
from datetime import datetime


# =========================================================
# FASTAPI APP
# =========================================================

app = FastAPI(title="Campus Helpdesk RAG Chatbot")


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# ADMIN LOGIN SETTINGS
# =========================================================

ADMIN_USERNAME = "Admin"
ADMIN_PASSWORD = "A2D2"

# Used for creating login tokens.
# For your college demo this is fine.
SECRET_KEY = "CampusHelpdeskSecretKey2026"


# =========================================================
# DATABASE
# =========================================================

DB_NAME = "chatbot.db"


def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def create_database():

    conn = get_db()

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            answer TEXT,
            timestamp TEXT NOT NULL,
            feedback TEXT
        )
        """
    )

    conn.commit()
    conn.close()


# Create database when backend starts
create_database()


# =========================================================
# TOKEN FUNCTIONS
# =========================================================

def create_token(username: str):

    timestamp = str(int(time.time()))

    data = username + ":" + timestamp

    signature = hmac.new(
        SECRET_KEY.encode("utf-8"),
        data.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    return data + ":" + signature


def verify_token(token: str):

    if not token:
        return False

    try:

        parts = token.split(":")

        if len(parts) != 3:
            return False

        username = parts[0]
        timestamp = parts[1]
        signature = parts[2]

        # Token expires after 2 hours
        if time.time() - int(timestamp) > 7200:
            return False

        data = username + ":" + timestamp

        expected_signature = hmac.new(
            SECRET_KEY.encode("utf-8"),
            data.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(
            signature,
            expected_signature
        )

    except (ValueError, TypeError):

        return False


def require_admin(authorization: str):

    if not authorization:

        raise HTTPException(
            status_code=401,
            detail="Admin login required"
        )

    if not authorization.startswith("Bearer "):

        raise HTTPException(
            status_code=401,
            detail="Invalid authorization"
        )

    token = authorization[len("Bearer "):]

    if not verify_token(token):

        raise HTTPException(
            status_code=401,
            detail="Invalid or expired admin session"
        )

    return True


# =========================================================
# HOME
# =========================================================

@app.get("/")
def home():

    return {
        "message": "Campus Helpdesk RAG Backend is running!"
    }


# =========================================================
# ADMIN LOGIN
# =========================================================

class LoginRequest(BaseModel):

    username: str
    password: str


@app.post("/admin/login")
def admin_login(data: LoginRequest):

    if (
        data.username == ADMIN_USERNAME
        and data.password == ADMIN_PASSWORD
    ):

        token = create_token(data.username)

        return {
            "success": True,
            "token": token
        }

    raise HTTPException(
        status_code=401,
        detail="Invalid username or password"
    )


# =========================================================
# QUESTION MODEL
# =========================================================

class Question(BaseModel):

    question: str


# =========================================================
# ASK CHATBOT
# =========================================================

@app.post("/ask")
def ask_question(data: Question):

    # Search your existing RAG/FAISS system
    results = search(data.question)

    if not results:

        answer = (
            "Sorry, I could not find relevant information."
        )

    else:

        answer = "\n\n".join(results)

    # Save question and answer for dashboard analytics
    conn = get_db()

    conn.execute(
        """
        INSERT INTO chats
        (question, answer, timestamp)
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


# =========================================================
# DASHBOARD - STATISTICS
# =========================================================

@app.get("/dashboard/stats")
def dashboard_stats(
    authorization: str = Header(default=None)
):

    require_admin(authorization)

    conn = get_db()

    total_questions = conn.execute(
        "SELECT COUNT(*) FROM chats"
    ).fetchone()[0]

    total_feedback = conn.execute(
        """
        SELECT COUNT(*)
        FROM chats
        WHERE feedback IS NOT NULL
        """
    ).fetchone()[0]

    positive_feedback = conn.execute(
        """
        SELECT COUNT(*)
        FROM chats
        WHERE feedback = 'positive'
        """
    ).fetchone()[0]

    negative_feedback = conn.execute(
        """
        SELECT COUNT(*)
        FROM chats
        WHERE feedback = 'negative'
        """
    ).fetchone()[0]

    today_questions = conn.execute(
        """
        SELECT COUNT(*)
        FROM chats
        WHERE date(timestamp)
        = date('now', 'localtime')
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


# =========================================================
# DASHBOARD - RECENT QUESTIONS
# =========================================================

@app.get("/dashboard/recent")
def recent_questions(
    authorization: str = Header(default=None)
):

    require_admin(authorization)

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


# =========================================================
# DASHBOARD - POPULAR QUESTIONS
# =========================================================

@app.get("/dashboard/popular")
def popular_questions(
    authorization: str = Header(default=None)
):

    require_admin(authorization)

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


# =========================================================
# DASHBOARD - QUESTIONS PER DAY
# =========================================================

@app.get("/dashboard/daily")
def daily_questions(
    authorization: str = Header(default=None)
):

    require_admin(authorization)

    conn = get_db()

    rows = conn.execute(
        """
        SELECT date(timestamp) AS day,
               COUNT(*) AS count
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


# =========================================================
# DASHBOARD - FEEDBACK
# =========================================================

class Feedback(BaseModel):

    chat_id: int
    feedback: str


@app.post("/dashboard/feedback")
def add_feedback(
    data: Feedback,
    authorization: str = Header(default=None)
):

    require_admin(authorization)

    if data.feedback not in ["positive", "negative"]:

        raise HTTPException(
            status_code=400,
            detail="Feedback must be positive or negative"
        )

    conn = get_db()

    cursor = conn.execute(
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

    if cursor.rowcount == 0:

        raise HTTPException(
            status_code=404,
            detail="Chat not found"
        )

    return {
        "success": True,
        "message": "Feedback saved"
    }
