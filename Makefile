
.PHONY: dev backend frontend

dev:
	@echo "Starting FastAPI + Streamlit..."
	@# Using a trap to kill background processes on exit is good practice but for simplicity we stick to the user's snippet logic
	@# running in background with &
	uv run uvicorn main:app --reload --host 0.0.0.0 --port 9000 & \
	uv run streamlit run app.py --server.address=0.0.0.0 --server.port=8501 --server.headless=true --browser.gatherUsageStats=false

backend:
	uv run uvicorn main:app --reload --host 0.0.0.0 --port 9000

frontend:
	uv run streamlit run app.py --server.address=0.0.0.0 --server.port=8501 --server.headless=true --browser.gatherUsageStats=false

