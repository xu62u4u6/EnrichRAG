"""FastAPI application."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from enrichrag.api.routes import router
from enrichrag.auth_store import init_storage
from enrichrag.settings import settings

# Optional URL prefix for obscurity when exposing to public network.
# Set URL_PREFIX="/<random-string>" in .env to enable.
_prefix = settings.url_prefix.strip("/")
prefix = f"/{_prefix}" if _prefix else ""

app = FastAPI(title="enrichRAG", version="0.2.0")
app.include_router(router, prefix=prefix)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

# Serve CSS/JS/assets under the prefix
app.mount(f"{prefix}/css", StaticFiles(directory=STATIC_DIR / "css"), name="css")
app.mount(f"{prefix}/js", StaticFiles(directory=STATIC_DIR / "js"), name="js")
app.mount(f"{prefix}/img", StaticFiles(directory=STATIC_DIR / "img"), name="img")


def _render_static_html(filename: str) -> HTMLResponse:
    html = (STATIC_DIR / filename).read_text(encoding="utf-8")
    if prefix:
        html = html.replace(
            "window.__API_PREFIX = '';",
            f"window.__API_PREFIX = '{prefix}';",
        )
        html = html.replace('href="css/', f'href="{prefix}/css/')
        html = html.replace('src="js/', f'src="{prefix}/js/')
        html = html.replace('src="img/', f'src="{prefix}/img/')
    return HTMLResponse(html)


@app.get(f"{prefix}/", response_class=HTMLResponse)
async def index():
    return _render_static_html("index.html")


@app.on_event("startup")
async def startup_event():
    init_storage()
