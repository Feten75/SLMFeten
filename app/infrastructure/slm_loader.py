import os
import ollama
import time
import psutil
from app.domain.slm_interface import ISLM

class SLMLoader(ISLM):
    def __init__(self):
        self.current_model_name = None
        self.actual_device = "Intel Iris Xe (GPU)"

    def _free_memory(self):
        """Libère le modèle actuel de la mémoire d'Ollama"""
        if self.current_model_name:
            try:
                print(f"--- [OLLAMA] Libération du modèle : {self.current_model_name} ---")
                ollama.generate(model=self.current_model_name, keep_alive=0)
                time.sleep(1)
            except Exception as e:
                print(f"Erreur lors de la libération : {e}")

    def load_model(self, model_name: str):
        try:
            self._free_memory()
            print(f"--- [OLLAMA] Vérification locale de : {model_name} ---")
            
            local_models_resp = ollama.list()
            model_exists = any(m.model == model_name for m in local_models_resp.models)

            if model_exists:
                print(f"--- [LOCAL] Modèle trouvé ! Chargement immédiat. ---")
            else:
                print(f"--- [DISTANT] Modèle absent. Téléchargement... ---")
                ollama.pull(model_name)
            
            self.current_model_name = model_name
            return f"Succès : {model_name} est chargé."

        except Exception as e:
            return f"ERREUR CHARGEMENT : {str(e)}"
    
    def generate(self, system_prompt: str, user_prompt: str):
        if not self.current_model_name:
            return {"error": "MODEL_NOT_LOADED"}

        start_time = time.time()
        try:
            response = ollama.generate(
                model=self.current_model_name,
                system=system_prompt, 
                prompt=user_prompt,
                options={
                    "num_thread": 8,
                    "num_ctx": 1024, 
                    "num_gpu": 1,         # Forcer l'usage du GPU
                    "num_predict": 40,  
                    "temperature": 0.1    # Basse température pour plus de précision (médical)
                },
                keep_alive="5m"           # Garde en mémoire 5min entre les tests si on ne change pas de modèle
            )
            
            end_time = time.time()
            inf_time = round(end_time - start_time, 3)

            total_ram_mb = 0
            for proc in psutil.process_iter(['name', 'memory_info']):
                try:
                    if "ollama" in proc.info['name'].lower():
                        total_ram_mb += proc.info['memory_info'].rss / (1024**2)
                except: continue

            return {
                "response": response['response'].strip(),
                "inference_time": inf_time,
                "tokens_generated": response.get('eval_count', 40),
                "consumption": {
                    "cpu_usage_percent": psutil.cpu_percent(),
                    "ram_allocated_mb": round(total_ram_mb, 2),
                    "ram_delta_mb": 0.0,
                    "device": self.actual_device
                }
            }
        except Exception as e:
            return {"error": f"Erreur génération : {str(e)}"}
        