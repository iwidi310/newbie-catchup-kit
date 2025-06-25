# PowerShell script to launch the FastAPI server
uvicorn rag_api.app:app --host 0.0.0.0 --port 8000 --reload
