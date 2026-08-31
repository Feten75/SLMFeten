from fastapi import APIRouter, HTTPException, status
from app.infrastructure.mongo_repository import MongoRepository
from app.core.auth_handler import hash_password, verify_password, create_access_token
from app.domain.user import User
from pydantic import BaseModel

router = APIRouter()
repo = MongoRepository()

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/login")
def login(request: LoginRequest):

    user = repo.find_by_username(request.username)
    if not user or not verify_password(request.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nom d'utilisateur ou mot de passe incorrect"
        )
    
    token = create_access_token({
        "sub": user["username"], 
        "role": user["role"]
    })
    
    return {
        "accessToken": token,
        "id": str(user["_id"]),
        "role": user["role"],
        "username": user["username"]
    }

@router.post("/register") 
def register(user: User):
    if repo.find_by_username(user.username):
        raise HTTPException(status_code=400, detail="Username déjà pris")
    
    user_dict = user.dict()
    user_dict["password"] = hash_password(user.password)
    
    repo.create_user(user_dict)
    return {"message": f"Compte créé pour {user.username}"}
