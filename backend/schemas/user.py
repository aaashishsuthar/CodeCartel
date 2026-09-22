from pydantic import BaseModel
from typing import Optional

class UserResponse(BaseModel):
    username: str
    role: str
    name: Optional[str] = None
    constituency: Optional[str] = None
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
