from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import pandas as pd
import os
import json

from ..database import get_db
from ..models.user import User
from ..schemas.user import Token, UserResponse
from ..services.auth_service import verify_password, create_access_token, get_password_hash
from ..security import get_current_user

router = APIRouter()

@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role}
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.post("/seed")
def seed_users(db: Session = Depends(get_db)):
    """
    Seeds the users table using mp_credentials.csv and portal_credentials.json.
    This creates the hashed passwords properly so we don't store plain text.
    """
    if db.query(User).first():
        return {"status": "already seeded"}
        
    BASE_DIR = r"c:/Users/Dream Different/OneDrive/Documents/vscode/New folder"
    
    # 1. Seed MPs
    csv_path = os.path.join(BASE_DIR, "mp_credentials.csv")
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        for _, row in df.iterrows():
            plain_pass = str(row["Password"])
            u = User(
                username=row["Username"],
                hashed_password=get_password_hash(plain_pass),
                role="MP",
                name=row["MP_Name"],
                constituency=row["Constituency"]
            )
            db.add(u)
            
    # 2. Seed Portal (CAG / Collector)
    json_path = os.path.join(BASE_DIR, "portal_credentials.json")
    if os.path.exists(json_path):
        with open(json_path, 'r') as f:
            creds = json.load(f)
            
        cag = creds.get("Ministry / CAG Auditors", {})
        if cag:
            db.add(User(
                username=cag["username"],
                hashed_password=get_password_hash(cag["password"]),
                role="CAG",
                name="Central Auditor"
            ))
            
        sna = creds.get("State Nodal Authorities (SNA)", {})
        if sna:
            db.add(User(
                username=sna["username"],
                hashed_password=get_password_hash(sna["password"]),
                role="SNA",
                name="State Nodal Officer"
            ))
            
        da = creds.get("District Authorities / Collectors", {})
        if da:
            db.add(User(
                username=da["username"],
                hashed_password=get_password_hash(da["password"]),
                role="COLLECTOR",
                name="District Collector"
            ))
            
    db.commit()
    return {"status": "success", "message": "Users seeded successfully"}
