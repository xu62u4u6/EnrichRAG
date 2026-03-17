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

VUE_UI_DIR = Path(__file__).resolve().parents[2] / "frontend-vue" / "dist"

# Serve Vue built assets
if (VUE_UI_DIR / "assets").exists():
    app.mount(f"{prefix}/assets", StaticFiles(directory=VUE_UI_DIR / "assets"), name="vue-assets")

# Serve Vue public directory files (e.g. /img/path1.svg)
VUE_PUBLIC_IMG = VUE_UI_DIR / "img"
if VUE_PUBLIC_IMG.exists():
    app.mount(f"{prefix}/img", StaticFiles(directory=VUE_PUBLIC_IMG), name="vue-img")


def _render_vue_html() -> HTMLResponse:
    index_path = VUE_UI_DIR / "index.html"
    if not index_path.exists():
        return HTMLResponse(
            "<h1>Vue UI build not found</h1><p>Run `npm run build` inside `frontend-vue/`.</p>",
            status_code=503,
        )
    html = index_path.read_text(encoding="utf-8")
    ui_base = f"{prefix}/" if prefix else "/"
    html = html.replace("__UI_BASE__", ui_base.rstrip("/") or "/")
    html = html.replace("__API_PREFIX__", prefix)
    html = html.replace('src="./assets/', f'src="{ui_base}assets/')
    html = html.replace('href="./assets/', f'href="{ui_base}assets/')
    return HTMLResponse(html)


@app.get(f"{prefix}/", response_class=HTMLResponse)
@app.get(f"{prefix}/{{full_path:path}}", response_class=HTMLResponse)
async def index(full_path: str = ""):
    if full_path.startswith("assets/") or full_path.startswith("img/"):
        return HTMLResponse(status_code=404, content="Not Found")
    return _render_vue_html()


@app.on_event("startup")
async def startup_event():
    init_storage()
