"""
Agent Kautilya — Direct Unified Launcher
Starts both the FastAPI Backend Engine and the Streamlit Frontend,
then automatically opens your web browser.
"""

import sys
import subprocess
import os
import webbrowser
import time
import urllib.request
import json

APP_DIR = os.path.dirname(os.path.abspath(__file__))

def is_backend_running():
    try:
        req = urllib.request.Request("http://127.0.0.1:8000/api/health", headers={"User-Agent": "Launcher"})
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            return resp.status == 200
    except Exception:
        return False

# 1. Ensure initial ML model and dataset artifacts exist
model_pkl = os.path.join(APP_DIR, "models", "artifacts", "model.pkl")
projects_csv = os.path.join(APP_DIR, "projects.csv")
if not os.path.exists(projects_csv) or not os.path.exists(model_pkl):
    print("Generating initial model and dataset with data_gen.py...")
    subprocess.run([sys.executable, os.path.join(APP_DIR, "data_gen.py")], cwd=APP_DIR, check=True)

# 2. Check and start FastAPI Backend if needed
backend_process = None
if not is_backend_running():
    print("Starting Agent Kautilya FastAPI Backend on http://127.0.0.1:8000 ...")
    backend_cmd = [
        sys.executable, "-m", "uvicorn", "backend.main:app",
        "--host", "127.0.0.1", "--port", "8000"
    ]
    backend_process = subprocess.Popen(backend_cmd, cwd=APP_DIR)
    
    # Wait for backend to be ready
    for _ in range(15):
        time.sleep(0.5)
        if is_backend_running():
            print("FastAPI Backend is online!")
            break
else:
    print("FastAPI Backend is already running on http://127.0.0.1:8000.")

# 3. Open Browser
print("Opening Agent Kautilya in your browser on http://localhost:8501 ...")
webbrowser.open("http://localhost:8501")

# 4. Run Streamlit Frontend
cmd = [sys.executable, "-m", "streamlit", "run", "app.py", "--server.headless", "false"]
try:
    subprocess.run(cmd, cwd=APP_DIR)
except KeyboardInterrupt:
    print("\nShutting down Agent Kautilya...")
finally:
    if backend_process:
        print("Stopping FastAPI Backend...")
        backend_process.terminate()
        try:
            backend_process.wait(timeout=3)
        except Exception:
            backend_process.kill()
    print("Shutdown complete.")
