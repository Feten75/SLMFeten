import os
import time
import gc
import psutil
from llama_cpp import Llama
from huggingface_hub import hf_hub_download
from app.domain.slm_interface import ISLM

class SLMLoader(ISLM):
    def __init__(self):
        self.model = None
        self.current_model_name = None
        self.actual_device = "Intel i9 (CPU AVX2 via llama.cpp)"
        self.DOWNLOAD_DIR = "models/modelsLammacpp"
        
        self.model_mapping = {
            "assistant_generiquev2": {"repo": "local", "file": "assistant_generiquev2.gguf"},
            "assistant_generique_feten": {"repo": "local", "file": "assistant_generique_final.gguf"},
            "medical-feten": {"repo": "local", "file": "medical_assistant_final_v2.gguf"},
            "llama3.2:1b": {"repo": "bartowski/Llama-3.2-1B-Instruct-GGUF", "file": "Llama-3.2-1B-Instruct-Q4_K_M.gguf"},
            "qwen2.5:1.5b": {"repo": "bartowski/Qwen2.5-1.5B-Instruct-GGUF", "file": "Qwen2.5-1.5B-Instruct-Q4_K_M.gguf"},
            "gemma2:2b": {"repo": "bartowski/gemma-2-2b-it-GGUF", "file": "gemma-2-2b-it-Q4_K_M.gguf"},
            "smollm2:1.7b": {"repo": "bartowski/SmolLM2-1.7B-Instruct-GGUF", "file": "SmolLM2-1.7B-Instruct-Q4_K_M.gguf"},
            "tinyllama": {"repo": "TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF", "file": "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"},
            "deepseek-r1:1.5b": {"repo": "unsloth/DeepSeek-R1-Distill-Qwen-1.5B-GGUF", "file": "DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf"},
            # new
            "smollm2:360m": {"repo": "bartowski/SmolLM2-360M-Instruct-GGUF", "file": "SmolLM2-360M-Instruct-Q4_K_M.gguf"},
            "smollm:135m": {"repo": "QuantFactory/SmolLM-135M-Instruct-GGUF", "file": "SmolLM-135M-Instruct.Q4_K_M.gguf"},
            "phi4:14b": {"repo": "bartowski/phi-4-GGUF", "file": "phi-4-Q4_K_M.gguf"},
            "llama3.1:8b": {"repo": "bartowski/Meta-Llama-3.1-8B-Instruct-GGUF", "file": "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"},
            "gemma3:4b": {"repo": "google/gemma-4-31B-it", "file": "gemma-4-31B-it.gguf"},
            "qwen3.5:2b": {"repo": "bartowski/Qwen2.5-3B-Instruct-GGUF", "file": "Qwen2.5-3B-Instruct-Q4_K_M.gguf"},
            "mistral:7b": {"repo": "bartowski/Mistral-7B-Instruct-v0.3-GGUF", "file": "Mistral-7B-Instruct-v0.3-Q4_K_M.gguf"}
        }

    def _free_memory(self):
        if self.model:
            del self.model
            self.model = None
            gc.collect()
            time.sleep(1)

    def load_model(self, model_name: str):
        try:
            self._free_memory()
            if model_name not in self.model_mapping:
                return f"ERREUR : Le modèle '{model_name}' n'est pas configuré."

            info = self.model_mapping[model_name]

            # 1. On construit le chemin relatif de base
            if info["repo"] == "local":
                rel_path = os.path.join(self.DOWNLOAD_DIR, info["file"])
            else:
                rel_path = hf_hub_download(
                    repo_id=info["repo"],
                    filename=info["file"],
                    local_dir=self.DOWNLOAD_DIR
                )

            # 2. ON FORCE LE CHEMIN ABSOLU (C'est l'étape cruciale pour Windows)
            # Cela transforme "models/modelsLammacpp/..." en "C:\Users\Feten Dridi\..."
            model_path = os.path.abspath(rel_path)
            
            # 3. Petit Print pour vérifier dans ton terminal
            print(f"--- [DEBUG] Chemin envoyé au moteur : {model_path} ---")

            if not os.path.exists(model_path):
                return f"ERREUR : Fichier introuvable à l'adresse : {model_path}"

            # 4. Chargement
            self.model = Llama(
                model_path=model_path,
                n_ctx=1024,
                n_threads=12,
                verbose=False
            )
            
            self.current_model_name = model_name
            return f"Succès : {model_name} est chargé et prêt."

        except Exception as e:
            return f"ERREUR CHARGEMENT : {str(e)}"
        
    def generate(self, system_prompt: str, user_prompt: str):
        if not self.model: 
            return {"error": "MODEL_NOT_LOADED"}
        
        process = psutil.Process(os.getpid())
        start_mem = process.memory_info().rss / (1024**2)
        psutil.cpu_percent(interval=None)

        prompt = f"<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\n{user_prompt}<|im_end|>\n<|im_start|>assistant\n"
        
        start_time = time.time()
        output = self.model(
            prompt, 
            max_tokens=40, 
            stop=["<|im_end|>", "<|endoftext|>", "User:"], 
            temperature=0.1
        )
        end_time = time.time()

        end_mem = process.memory_info().rss / (1024**2)
        cpu_val = psutil.cpu_percent(interval=None)

        return {
            "response": output['choices'][0]['text'].strip(),
            "inference_time": round(end_time - start_time, 3),
            "tokens_generated": output['usage']['completion_tokens'],
            "consumption": {
                "cpu_usage_percent": cpu_val,          
                "ram_allocated_mb": round(end_mem, 2), 
                "ram_delta_mb": round(max(0, end_mem - start_mem), 2),
                "device": self.actual_device
            }
        }
    
    