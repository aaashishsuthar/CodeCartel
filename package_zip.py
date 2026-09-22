"""
Refreshes Agent_Kautilya_SIH2026.zip with the latest clean workspace files.
"""

import os
import zipfile

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
ZIP_NAME = os.path.join(ROOT_DIR, "Agent_Kautilya_SIH2026.zip")

EXCLUDE_DIRS = {
    "__pycache__", ".git", ".pytest_cache", ".gemini", "node_modules", ".venv", "venv", ".idea", ".vscode"
}
EXCLUDE_EXTS = {".pyc", ".pyo", ".pyd", ".zip"}

def make_archive():
    count = 0
    with zipfile.ZipFile(ZIP_NAME, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(ROOT_DIR):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith(".")]
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in EXCLUDE_EXTS:
                    continue
                if file.startswith("."):
                    continue
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, ROOT_DIR)
                zf.write(abs_path, rel_path)
                count += 1
    print(f"Refreshed {ZIP_NAME} with {count} files.")

if __name__ == "__main__":
    make_archive()
