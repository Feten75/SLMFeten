from app.infrastructure.slm_loader import SLMLoader
from app.infrastructure.mongo_repository import MongoRepository

class SLMService:

    def __init__(self):
        self.loader = SLMLoader()
        self.repository = MongoRepository()
        self.current_model = None

    def load(self, model_name: str):
        # On stocke le nom du modèle actuel pour les logs
        self.current_model = model_name
        return self.loader.load_model(model_name)

    def infer(self, system_prompt: str, user_prompt: str):
        result = self.loader.generate(system_prompt, user_prompt)
        
        if "error" in result:
            return result

        # Enregistrement dans MongoDB avec les métriques détaillées
        log_data = {
            "model_used": self.current_model,
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "ai_response": result["response"],
            "inference_time": result["inference_time"],
            "tokens_generated": result["tokens_generated"],
            "metrics": {
                "cpu_percent": result["consumption"]["cpu_usage_percent"],
                "ram_total_mb": result["consumption"]["ram_allocated_mb"],
                "ram_impact_mb": result["consumption"]["ram_delta_mb"],
                "device": result["consumption"]["device"]
            }
        }
        
        self.repository.save(log_data)
        return result