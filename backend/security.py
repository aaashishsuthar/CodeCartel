from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from typing import List, Callable, Optional

from .database import get_db
from .models.user import User
from .services.auth_service import SECRET_KEY, ALGORITHM

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user

def get_optional_current_user(token: Optional[str] = Depends(oauth2_scheme_optional), db: Session = Depends(get_db)) -> Optional[User]:
    """Returns User if valid bearer token provided, else None (public citizen)."""
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username:
            return db.query(User).filter(User.username == username).first()
    except Exception:
        pass
    return None

def require_roles(*allowed_roles: str) -> Callable:
    """
    Dependency factory to enforce role-based access control (RBAC).
    Allowed roles can be e.g. "CAG", "COLLECTOR", "MP".
    """
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: User role '{current_user.role}' is not authorized. Required: {', '.join(allowed_roles)}"
            )
        return current_user
    return role_checker

def validate_project_access(project, current_user: User):
    """
    Ensures that MPs can only access their own constituency's projects.
    CAG and COLLECTOR have broader jurisdiction.
    """
    if current_user.role == "MP":
        mp_matches = current_user.name and project.mp_name and current_user.name.strip().lower() == project.mp_name.strip().lower()
        const_matches = current_user.constituency and project.constituency and current_user.constituency.strip().lower() == project.constituency.strip().lower()
        if not (mp_matches or const_matches):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You do not have permission to view or audit projects outside your constituency."
            )
    elif current_user.role == "COLLECTOR":
        if current_user.constituency and project.constituency:
            if current_user.constituency.strip().lower() != project.constituency.strip().lower():
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Project is outside your district jurisdiction."
                )
