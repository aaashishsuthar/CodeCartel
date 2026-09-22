import joblib
import os
from .features import extract_features

BASE_DIR = r"c:/Users/Dream Different/OneDrive/Documents/vscode/New folder"
MODEL_PATH = os.path.join(BASE_DIR, "models", "artifacts", "model.pkl")

class MLPredictor:
    def __init__(self):
        self.artifacts = None
        self._load_model()
        
    def _load_model(self):
        if os.path.exists(MODEL_PATH):
            self.artifacts = joblib.load(MODEL_PATH)
            
    def predict(self, project):
        if not self.artifacts:
            return 0.0
            
        clf = self.artifacts["clf"]
        scaler = self.artifacts["scaler"]
        feature_cols = self.artifacts["feature_cols"]
        work_types = self.artifacts["work_types"]
        
        X = extract_features(project, feature_cols, work_types)
        X_s = scaler.transform(X)
        
        prob = clf.predict_proba(X_s)[0, 1]
        return float(prob)
        
predictor = MLPredictor()
