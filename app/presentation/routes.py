'''from fastapi import APIRouter
from pydantic import BaseModel
from app.application.slm_service import SLMService
from app.core.config import AVAILABLE_MODELS
from fastapi import APIRouter, HTTPException, status

router = APIRouter()
service = SLMService()

class GenerateRequest(BaseModel):
    system_prompt: str
    user_prompt: str

@router.post("/load_model")
def load_model(model_name: str):
    if model_name not in AVAILABLE_MODELS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Le modèle '{model_name}' n'est pas configuré dans AVAILABLE_MODELS."
        )
    
    msg = service.load(model_name)
    return {"message": msg}


@router.post("/generate")
def generate(request: GenerateRequest):
    result = service.infer(request.system_prompt, request.user_prompt)
    
    if "error" in result:
        if result["error"] == "MODEL_NOT_LOADED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Erreur: Aucun modèle n'est en mémoire. Utilisez /load_model d'abord."
            )
    return result

@router.get("/models")
def list_models():
    return {"available_models": AVAILABLE_MODELS}
'''

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from app.application.slm_service import SLMService
from app.core.config import AVAILABLE_MODELS

# 1. IL FAUT ABSOLUMENT DÉCLARER LE ROUTER ET LE SERVICE ICI
router = APIRouter()
service = SLMService()

# 2. DÉFINITION DE LA STRUCTURE DE LA REQUÊTE
class GenerateRequest(BaseModel):
    call_id: str  # ID unique pour la mémoire (Short-term / State)
    phone: str    # Numéro pour la mémoire long terme
    user_prompt: str

# 3. LES ROUTES
@router.post("/load_model")
def load_model(model_name: str):
    if model_name not in AVAILABLE_MODELS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Le modèle '{model_name}' n'est pas configuré dans AVAILABLE_MODELS."
        )
    
    msg = service.load(model_name)
    return {"message": msg}

@router.post("/generate")
def generate(request: GenerateRequest):
    # On utilise la nouvelle fonction "infer_with_memory" créée dans SLMService
    result = service.infer_with_memory(
        call_id=request.call_id, 
        phone=request.phone, 
        user_input=request.user_prompt
    )
    
    if "error" in result:
        if result["error"] == "MODEL_NOT_LOADED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Erreur: Aucun modèle n'est en mémoire. Utilisez /load_model d'abord."
            )
    return result

@router.get("/models")
def list_models():
    return {"available_models": AVAILABLE_MODELS}
