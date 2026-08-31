from pydantic import BaseModel, EmailStr
from typing import Optional

class User(BaseModel):
    username: str
    password: str
    role: str  # "ADMIN", "USER"
    nom: Optional[str] = None
    prenom: Optional[str] = None
    email: Optional[EmailStr] = None
    telephone: Optional[str] = None
