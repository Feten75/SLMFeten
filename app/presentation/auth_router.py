from fastapi import APIRouter, HTTPException, status
from app.infrastructure.mongo_repository import MongoRepository
from app.core.auth_handler import hash_password, verify_password, create_access_token
from app.domain.user import User
from pydantic import BaseModel

router = APIRouter()
repo = MongoRepository()

# DTO pour le login (équivalent de AuthRequest en Java)
class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/login")
def login(request: LoginRequest):
    # 1. Chercher l'utilisateur (UserRepository.findByUsername)
    user = repo.find_by_username(request.username)
    
    # 2. Vérifier si l'utilisateur existe et si le mot de passe match (passwordEncoder.matches)
    if not user or not verify_password(request.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nom d'utilisateur ou mot de passe incorrect"
        )
    
    # 3. Générer le token (jwtService.generateToken)
    token = create_access_token({
        "sub": user["username"], 
        "role": user["role"]
    })
    
    # Retourne la réponse (équivalent de ResponseLogin)
    return {
        "accessToken": token,
        "id": str(user["_id"]),
        "role": user["role"],
        "username": user["username"]
    }

@router.post("/register") # Route pour que l'Admin crée des comptes
def register(user: User):
    # Vérifier si déjà existant
    if repo.find_by_username(user.username):
        raise HTTPException(status_code=400, detail="Username déjà pris")
    
    user_dict = user.dict()
    # Hasher le mot de passe avant enregistrement
    user_dict["password"] = hash_password(user.password)
    
    repo.create_user(user_dict)
    return {"message": f"Compte créé pour {user.username}"}
