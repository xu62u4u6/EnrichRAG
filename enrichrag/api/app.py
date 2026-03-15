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
VUE_UI_DIR = Path(__file__).resolve().parents[2] / "frontend-vue" / "dist"

# Serve CSS/JS/assets under the prefix
app.mount(f"{prefix}/css", StaticFiles(directory=STATIC_DIR / "css"), name="css")
app.mount(f"{prefix}/js", StaticFiles(directory=STATIC_DIR / "js"), name="js")
app.mount(f"{prefix}/img", StaticFiles(directory=STATIC_DIR / "img"), name="img")
if (VUE_UI_DIR / "assets").exists():
    app.mount(f"{prefix}/ui-vue/assets", StaticFiles(directory=VUE_UI_DIR / "assets"), name="ui-vue-assets")


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


def _render_vue_html() -> HTMLResponse:
    index_path = VUE_UI_DIR / "index.html"
    if not index_path.exists():
        return HTMLResponse(
            "<h1>Vue UI build not found</h1><p>Run `npm run build` inside `frontend-vue/`.</p>",
            status_code=503,
        )
    html = index_path.read_text(encoding="utf-8")
    ui_base = f"{prefix}/ui-vue" if prefix else "/ui-vue"
    html = html.replace("__UI_BASE__", ui_base)
    html = html.replace("__API_PREFIX__", prefix)
    html = html.replace('src="./assets/', f'src="{ui_base}/assets/')
    html = html.replace('href="./assets/', f'href="{ui_base}/assets/')
    return HTMLResponse(html)


@app.get(f"{prefix}/", response_class=HTMLResponse)
async def index():
    return _render_static_html("index.html")


@app.get(f"{prefix}/ui-vue", response_class=HTMLResponse)
@app.get(f"{prefix}/ui-vue/{{full_path:path}}", response_class=HTMLResponse)
async def vue_index(full_path: str = ""):
    if full_path.startswith("assets/"):
        return HTMLResponse(status_code=404, content="Not Found")
    return _render_vue_html()


@app.on_event("startup")
async def startup_event():
    init_storage()
