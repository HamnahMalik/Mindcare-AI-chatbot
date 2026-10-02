from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from sessions import init_db
from chatbot import mindcare_chat


app = FastAPI(
    title="MindCare API",
    version="1.0.0"
)

init_db()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    user_id: str
    message: str


@app.get("/")
def home():
    return FileResponse("/app/static/index.html")


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


@app.post("/chat")
def chat(request: ChatRequest):

    reply = mindcare_chat(
        request.user_id,
        request.message
    )

    return {
        "user_id": request.user_id,
        "reply": reply
    }
