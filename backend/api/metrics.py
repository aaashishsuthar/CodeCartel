from fastapi import APIRouter
import json
import os

router = APIRouter()
BASE_DIR = r"c:/Users/Dream Different/OneDrive/Documents/vscode/New folder"
METRICS_PATH = os.path.join(BASE_DIR, "model_metrics.json")

BENCHMARK_METRICS = {
    "accuracy": 0.953,
    "precision": 0.723,
    "recall": 0.935,
    "f1": 0.815,
    "test_size": 831,
    "positive_rate": 0.111,
    "tn": 706,
    "fp": 33,
    "fn": 6,
    "tp": 86
}

@router.get("/model/metrics")
def get_model_metrics():
    if os.path.exists(METRICS_PATH):
        try:
            with open(METRICS_PATH, "r") as f:
                return json.load(f)
        except Exception:
            pass
            
    return BENCHMARK_METRICS
