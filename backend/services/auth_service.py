import bcrypt
from jose import JWTError, jwt
from datetime import datetime, timedelta

SECRET_KEY = "KAUTILYA_SUPER_SECRET_KEY_2026"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120

def verify_password(plain_password, hashed_password):
    # bcrypt expects bytes
    if isinstance(plain_password, str):
        plain_password = plain_password.encode('utf-8')
    if isinstance(hashed_password, str):
        hashed_password = hashed_password.encode('utf-8')
    return bcrypt.checkpw(plain_password, hashed_password)

def get_password_hash(password):
    if isinstance(password, str):
        password = password.encode('utf-8')
    return bcrypt.hashpw(password, bcrypt.gensalt()).decode('utf-8')

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def authenticate_user(db, username: str, password: str):
    """
    Authenticates a user against the database.
    If the database is not yet seeded, transparently resolves and seeds from
    portal_credentials.json or mp_credentials.csv.
    """
    import os
    import json
    import pandas as pd
    from ..models.user import User

    if db is not None:
        try:
            user = db.query(User).filter(User.username == username).first()
            if user and verify_password(password, user.hashed_password):
                return user
        except Exception:
            user = None

    # Fallback to credential files
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # 1. Check portal credentials (CAG, SNA, Collector)
    portal_path = os.path.join(base_dir, "portal_credentials.json")
    if os.path.exists(portal_path):
        try:
            with open(portal_path, "r", encoding="utf-8") as f:
                portal_creds = json.load(f)

            role_meta = {
                "Ministry / CAG Auditors": ("CAG", "Central Auditor"),
                "State Nodal Authorities (SNA)": ("SNA", "State Nodal Officer"),
                "District Authorities / Collectors": ("COLLECTOR", "District Collector")
            }

            for portal_name, info in portal_creds.items():
                if info.get("username") == username and info.get("password") == password:
                    r_code, r_name = role_meta.get(portal_name, ("CAG", "Authorized Officer"))
                    if db is not None:
                        try:
                            existing = db.query(User).filter(User.username == username).first()
                            if existing:
                                existing.hashed_password = get_password_hash(password)
                                existing.role = r_code
                                db.commit()
                                return existing
                            new_u = User(
                                username=username,
                                hashed_password=get_password_hash(password),
                                role=r_code,
                                name=r_name
                            )
                            db.add(new_u)
                            db.commit()
                            db.refresh(new_u)
                            return new_u
                        except Exception:
                            db.rollback()

                    # Return standalone user instance if DB transaction fails
                    return User(username=username, hashed_password=get_password_hash(password), role=r_code, name=r_name)
        except Exception:
            pass

    # 2. Check MP credentials
    mp_csv = os.path.join(base_dir, "mp_credentials.csv")
    if os.path.exists(mp_csv):
        try:
            mdf = pd.read_csv(mp_csv)
            match = mdf[(mdf["Username"].astype(str) == str(username)) & (mdf["Password"].astype(str) == str(password))]
            if not match.empty:
                row = match.iloc[0]
                if db is not None:
                    try:
                        existing = db.query(User).filter(User.username == username).first()
                        if existing:
                            existing.hashed_password = get_password_hash(password)
                            existing.role = "MP"
                            db.commit()
                            return existing
                        new_u = User(
                            username=username,
                            hashed_password=get_password_hash(password),
                            role="MP",
                            name=str(row.get("MP_Name", username)),
                            constituency=str(row.get("Constituency", ""))
                        )
                        db.add(new_u)
                        db.commit()
                        db.refresh(new_u)
                        return new_u
                    except Exception:
                        db.rollback()

                return User(
                    username=username,
                    hashed_password=get_password_hash(password),
                    role="MP",
                    name=str(row.get("MP_Name", username)),
                    constituency=str(row.get("Constituency", ""))
                )
        except Exception:
            pass

    return None

