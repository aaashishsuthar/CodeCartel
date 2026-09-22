def validate_project_record(record: dict):
    errors = []
    warnings = []
    
    if not record.get("Project_ID"):
        errors.append("Missing project ID")
        
    sanctioned = record.get("Sanctioned_Amount")
    if not sanctioned or str(sanctioned).strip() == "":
        errors.append("Missing amounts")
    elif float(sanctioned) < 0:
        errors.append("Invalid amounts")
        
    expenditure = record.get("UC_Amount")
    if expenditure and str(expenditure).strip() != "" and sanctioned and str(sanctioned).strip() != "":
        if float(expenditure) < 0:
            errors.append("Negative expenditure")
        if float(expenditure) > float(sanctioned):
            warnings.append("Expenditure greater than sanctioned amount")
            
    if not record.get("Constituency"):
        warnings.append("Missing constituency")
        
    return len(errors) == 0, errors, warnings
