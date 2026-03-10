"""FastAPI application."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from enrichrag.api.routes import router

app = FastAPI(title="enrichRAG", version="0.1.0")
app.include_router(router)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@app.get("/", response_class=HTMLResponse)
async def index():
    index_file = STATIC_DIR / "index.html"
    return HTMLResponse(index_file.read_text(encoding="utf-8"))
