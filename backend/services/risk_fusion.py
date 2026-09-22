from ..ml.predictor import predictor
from ..rules.engine import apply_rules

def calculate_risk(project):
    """
    Takes a ProjectModel and calculates Risk_Score based on Hybrid Risk Engine.
    Risk_Score = max(Model_Probability, Rule_Signal)
    """
    
    ml_prob = predictor.predict(project)
    rules_out = apply_rules(project)
    rule_signal = rules_out["rule_signal"]
    
    risk_score = round(max(ml_prob, rule_signal), 3)
    
    if risk_score > 0.66:
        risk_level = "High"
    elif risk_score > 0.33:
        risk_level = "Medium"
    else:
        risk_level = "Low"
        
    return {
        "ml_probability": round(ml_prob, 3),
        "rule_signal": round(rule_signal, 3),
        "risk_score": risk_score,
        "risk_level": risk_level,
        "rules": rules_out
    }
