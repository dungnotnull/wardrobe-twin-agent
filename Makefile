.PHONY: help install install-ml install-ui dev-server dev-ui dev lint clean test

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install Python backend (core only, no heavy ML)
	pip install -e .

install-ml: ## Install Python backend with heavy ML deps (detectron2, SAM, mediapipe)
	pip install -e ".[ml-heavy]"

install-ui: ## Install UI dependencies
	cd ui && npm install

install-all: install install-ui ## Install everything (core backend + UI)

dev-server: ## Start the FastAPI backend server
	python -m backend.api.server

dev-ui: ## Start the Vite dev server for UI
	cd ui && npm run dev

dev-electron: ## Start Electron + Vite dev
	cd ui && npm run electron:dev

dev: ## Start both backend and UI (run in separate terminals)
	@echo "Start backend:  make dev-server"
	@echo "Start UI:        make dev-ui"

lint: ## Run Python linter
	ruff check backend/ config/

typecheck: ## Run Python type checker
	mypy backend/ config/ --ignore-missing-imports

clean: ## Remove generated files
	rm -rf .venv/ data/models/*.pth data/avatars/*.obj data/wardrobe_images/*.png data/cache/* ui/node_modules ui/dist
	find . -type d -name __pycache__ -exec rm -rf {} +

test: ## Run tests
	pytest tests/ -v
