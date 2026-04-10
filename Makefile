.PHONY: dev build start frontend backend clean kg-build deploy

DEPLOY_DIR ?= $(HOME)/enrichrag-prod

# ── Dev (frontend build + backend on port 9002) ──
dev: build
	uv run uvicorn enrichrag.api.app:app --host 0.0.0.0 --port 9002 --reload

# ── Frontend ──
frontend:
	cd frontend && npm run dev

build:
	cd frontend && npm run build

# ── Backend ──
backend:
	uv run uvicorn enrichrag.api.app:app --host 0.0.0.0 --port 9001 --reload

# ── Deploy (copy to separate directory, serves on port 9001, isolated from dev) ──
deploy:
	@echo "Deploying to $(DEPLOY_DIR)..."
	mkdir -p $(DEPLOY_DIR)
	rsync -a --delete \
		--exclude='.git' \
		--exclude='node_modules' \
		--exclude='__pycache__' \
		--exclude='dist-snapshot-*' \
		--exclude='.env' \
		./ $(DEPLOY_DIR)/
	cp .env $(DEPLOY_DIR)/.env
	cd $(DEPLOY_DIR) && uv sync && cd frontend && npm ci
	@echo "Done. Start with: cd $(DEPLOY_DIR) && make start"

# ── Start (production, no reload) ──
start: build
	uv run uvicorn enrichrag.api.app:app --host 0.0.0.0 --port 9001

# ── Knowledge Graph ──
kg-build:
	uv run enrichrag kg build

kg-rebuild:
	uv run enrichrag kg build --force

# ── Utilities ──
typecheck:
	cd frontend && npx vue-tsc --noEmit

lint:
	uv run ruff check enrichrag/
	cd frontend && npx eslint src/

clean:
	rm -rf frontend/dist
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
