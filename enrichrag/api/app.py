"""FastAPI application."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from enrichrag.api.routes import router
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


@app.get(f"{prefix}/", response_class=HTMLResponse)
async def index():
    index_file = STATIC_DIR / "index.html"
    html = index_file.read_text(encoding="utf-8")
    # Inject API prefix so frontend JS knows where to call
    if prefix:
        html = html.replace(
            "window.__API_PREFIX = '';",
            f"window.__API_PREFIX = '{prefix}';",
        )
        # Rewrite relative asset paths to include prefix
        html = html.replace('href="css/', f'href="{prefix}/css/')
        html = html.replace('src="js/', f'src="{prefix}/js/')
    return HTMLResponse(html)
