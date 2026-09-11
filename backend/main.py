from fastapi import FastAPI
from pydantic import BaseModel
from rag.query import search
import ollama

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

    # 1. Search college documents using FAISS
    results = search(data.question)

    if not results:
        return {
            "answer": "Sorry, I could not find relevant information in the college documents."
        }

    # 2. Combine retrieved information
    context = "\n\n".join(results)

    # 3. Send context + question to Llama 3
    prompt = f"""
You are a Campus Helpdesk AI assistant.

Answer the student's question using ONLY the information provided
in the context below.

If the answer is not available in the context, say:
"I could not find this information in the available college documents."

Do not invent college rules, dates, timings, procedures, or policies.

Context:
{context}

Student Question:
{data.question}

Answer clearly and briefly:
"""

    # 4. Generate answer using Ollama
    response = ollama.chat(
        model="llama3",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    answer = response["message"]["content"]

    return {
        "answer": answer
    }