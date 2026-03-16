.PHONY: dev build start stop frontend backend clean kg-build

# ── Dev (frontend build + backend, single command) ──
dev: build backend

# ── Frontend ──
frontend:
	cd frontend-vue && npm run dev

build:
	cd frontend-vue && npm run build

# ── Backend ──
backend:
	uv run uvicorn enrichrag.api.app:app --host 0.0.0.0 --port 9001 --reload

# ── Start (production-like, no reload) ──
start: build
	uv run uvicorn enrichrag.api.app:app --host 0.0.0.0 --port 9001

# ── Knowledge Graph ──
kg-build:
	uv run enrichrag kg build

kg-rebuild:
	uv run enrichrag kg build --force

# ── Utilities ──
typecheck:
	cd frontend-vue && npx vue-tsc --noEmit

lint:
	uv run ruff check enrichrag/
	cd frontend-vue && npx eslint src/

clean:
	rm -rf frontend-vue/dist
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
