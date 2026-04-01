import torch
import os
import time
import gc
import psutil
from transformers import AutoTokenizer
from optimum.intel import OVModelForCausalLM, OVWeightQuantizationConfig
from app.domain.slm_interface import ISLM

class SLMLoader(ISLM):
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.current_model_name = None
        self.actual_device = "Unknown"

    def _free_memory(self):
        if self.model is not None:
            self.model = None
            self.tokenizer = None
            gc.collect()
            time.sleep(0.5)

    def load_model(self, model_name: str):
        # --- SÉCURITÉ CRITIQUE ---
        if model_name is None:
            return "ERREUR : Le nom du modèle reçu est 'None'."
        
        # On s'assure que c'est bien une chaîne de caractères
        model_name = str(model_name)
        print(f"--- [DEBUG] Tentative de chargement de : '{model_name}' ---")
        
        self._free_memory()
        
        try:
            # 1. Déterminer si c'est un GGUF ou un modèle standard
            is_gguf = model_name.lower().endswith(".gguf")
            
            # 2. Gérer le chemin local (dossier 'models')
            safe_name = model_name.replace("/", os.sep)
            local_path = os.path.normpath(os.path.join("models", safe_name))
            
            # On choisit le chemin à charger
            if is_gguf:
                path_to_load = model_name
            elif os.path.exists(local_path):
                path_to_load = local_path
                print(f"--- [LOCAL] Trouvé sur le disque : {path_to_load}")
            else:
                path_to_load = model_name
                print(f"--- [HF] Téléchargement requis : {path_to_load}")

            # 3. Charger le Tokenizer
            # Pour les GGUF locaux, on peut avoir besoin d'un tokenizer HF par défaut
            try:
                self.tokenizer = AutoTokenizer.from_pretrained(path_to_load)
            except:
                self.tokenizer = AutoTokenizer.from_pretrained("gpt2") 

            # 4. Vérifier si OpenVINO existe déjà
            ov_exists = False
            if not is_gguf and os.path.isdir(path_to_load):
                ov_exists = os.path.exists(os.path.join(path_to_load, "openvino_model.xml"))

            # 5. CONFIGURATION INTEL (Fix group_size=64 pour les petits modèles)
            q_config = OVWeightQuantizationConfig(bits=4, sym=True, group_size=64)

            common_opts = {
                "export": not ov_exists if not is_gguf else True,
                "quantization_config": q_config if (not ov_exists and not is_gguf) else None,
                "compile": True,
                "cache_dir": "./model_cache"
            }

            # 6. CHARGEMENT (Priorité GPU Iris Xe, sinon CPU i9)
            try:
                print("Tentative sur GPU Iris Xe...")
                self.model = OVModelForCausalLM.from_pretrained(
                    path_to_load, device="GPU", ov_config={"PERFORMANCE_HINT": "LATENCY"}, **common_opts
                )
                self.actual_device = "GPU (Iris Xe)"
            except Exception as e:
                print(f"Repli sur CPU i9 (Raison: {e})")
                self.model = OVModelForCausalLM.from_pretrained(
                    path_to_load, device="CPU", ov_config={"PERFORMANCE_HINT": "LATENCY", "INFERENCE_NUM_THREADS": "8"}, **common_opts
                )
                self.actual_device = "CPU (i9)"

            # 7. Sauvegarde locale pour les prochaines fois (Instantané)
            if not ov_exists and not is_gguf:
                print(f"Sauvegarde du modèle optimisé dans {local_path}...")
                os.makedirs(local_path, exist_ok=True)
                self.model.save_pretrained(local_path)

            self.current_model_name = model_name
            return f"Succès : {model_name} chargé sur {self.actual_device}."

        except Exception as global_err:
            return f"ERREUR FATALE DURANT LE CHARGEMENT : {str(global_err)}"

    def generate(self, system_prompt: str, user_prompt: str):
        if self.model is None or self.tokenizer is None:
            return {"error": "MODEL_NOT_LOADED"}

        # --- MESURE DES RESSOURCES ---
        process = psutil.Process(os.getpid())
        start_mem = process.memory_info().rss / (1024**2) # MB
        psutil.cpu_percent(interval=None) # Reset CPU

        full_prompt = (
            f"<|im_start|>system\n{system_prompt}<|im_end|>\n"
            f"<|im_start|>user\n{user_prompt}<|im_end|>\n"
            f"<|im_start|>assistant\n"
        )
        
        inputs = self.tokenizer(full_prompt, return_tensors="pt")
        
        start_time = time.time()
        with torch.no_grad():
            outputs = self.model.generate(**inputs, max_new_tokens=40, do_sample=False)
        end_time = time.time()

        # --- CALCUL CONSOMMATION ---
        end_mem = process.memory_info().rss / (1024**2)
        cpu_val = psutil.cpu_percent(interval=None)

        response = self.tokenizer.decode(outputs[0][inputs.input_ids.shape[-1]:], skip_special_tokens=True)

        return {
            "response": response.strip(),
            "inference_time": round(end_time - start_time, 3),
            "tokens_generated": len(outputs[0]) - inputs.input_ids.shape[-1],
            "consumption": {
                "cpu_usage_percent": cpu_val,
                "ram_allocated_mb": round(end_mem, 2),
                "ram_delta_mb": round(max(0, end_mem - start_mem), 2),
                "device": self.actual_device
            }
        }
        