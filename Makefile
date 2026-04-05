
.PHONY: dev backend frontend clean release

# Variables
PORT_BACKEND = 9000
PORT_FRONTEND = 8501

dev: clean
	@echo "Starting FastAPI + Streamlit..."
ifeq ($(OS),Windows_NT)
	@cmd /c start /B uv run uvicorn main:app --reload --host 0.0.0.0 --port $(PORT_BACKEND)
	@uv run streamlit run app.py --server.address=0.0.0.0 --server.port=$(PORT_FRONTEND) --server.headless=true --browser.gatherUsageStats=false
else
	@uv run uvicorn main:app --reload --host 0.0.0.0 --port $(PORT_BACKEND) & \
	uv run streamlit run app.py --server.address=0.0.0.0 --server.port=$(PORT_FRONTEND) --server.headless=true --browser.gatherUsageStats=false
endif

backend:
	uv run uvicorn main:app --reload --host 0.0.0.0 --port $(PORT_BACKEND)

frontend:
	uv run streamlit run app.py --server.address=0.0.0.0 --server.port=$(PORT_FRONTEND) --server.headless=true --browser.gatherUsageStats=false

clean:
	@echo "Cleaning up ports $(PORT_BACKEND) and $(PORT_FRONTEND)..."
ifeq ($(OS),Windows_NT)
	@powershell -Command "Get-NetTCPConnection -LocalPort $(PORT_BACKEND),$(PORT_FRONTEND) -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $$_.OwningProcess -Force }" 2>nul || exit 0
else
	@fuser -k $(PORT_BACKEND)/tcp $(PORT_FRONTEND)/tcp 2>/dev/null || true
endif

# Usage: make release VERSION=v1.2.0
release:
	@if [ -z "$(VERSION)" ]; then echo "Usage: make release VERSION=v1.0.0"; exit 1; fi
	@echo "Tagging $(VERSION) and pushing to trigger GitHub Actions release build..."
	git tag $(VERSION)
	git push origin $(VERSION)

