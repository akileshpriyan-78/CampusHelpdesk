from fastapi import FastAPI
from pydantic import BaseModel
from rag.query import search

app = FastAPI(title="Campus Helpdesk RAG Chatbot")


@app.get("/")
def home():
    return {
        "message": "Campus Helpdesk RAG Backend is running!"
    }


class Question(BaseModel):
    question: str


@app.post("/ask")
def ask_question(data: Question):

    results = search(data.question)

    if not results:
        return {
            "answer": "Sorry, I could not find relevant information."
        }

    answer = "\n\n".join(results)

    return {
        "answer": answer
    }