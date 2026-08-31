from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from app.application.slm_service import SLMService
from app.core.config import AVAILABLE_MODELS

router = APIRouter()
service = SLMService()

class GenerateRequest(BaseModel):
    call_id: str
    phone: str
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
