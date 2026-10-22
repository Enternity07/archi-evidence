"""Optional FastAPI service. Online requests require an explicit --online CLI."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .agent import extractive_answer
from .retrieval import KnowledgeBase

ROOT = Path(__file__).resolve().parents[1]


class Question(BaseModel):
    question: str = Field(min_length=1, max_length=2000, pattern=r"\S")
    top_k: int = Field(default=3, ge=1, le=8, strict=True)


def create_app(db=None):
    app = FastAPI(title="ArchiEvidence", version="0.1.0")
    knowledge = KnowledgeBase(db or ROOT / "data" / "knowledge.sqlite3")

    @app.get("/api/health")
    def health():
        return {"status": "ok", "mode": "offline-extractive", "chunks": knowledge.count()}

    @app.post("/api/ask")
    def ask(body: Question):
        return extractive_answer(body.question, knowledge, body.top_k)

    @app.get("/")
    def index():
        return FileResponse(ROOT / "static" / "index.html")

    @app.get("/app.js")
    def script():
        return FileResponse(ROOT / "static" / "app.js", media_type="application/javascript")

    @app.get("/style.css")
    def style():
        return FileResponse(ROOT / "static" / "style.css", media_type="text/css")

    return app
