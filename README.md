from fastapi import FastAPI

app = FastAPI(title="Campus Helpdesk RAG Chatbot")


@app.get("/")
def home():
    return {
        "message": "Campus Helpdesk RAG Backend is running!"
    }
    GitHub connection tested successfully.
    My first GitHub update