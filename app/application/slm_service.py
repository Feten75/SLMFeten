import time
import re
import json # Nécessaire pour parser la réponse de l'IA
from app.infrastructure.slm_loader import SLMLoader
from app.infrastructure.mongo_repository import MongoRepository
from app.domain.entities.appointment_memory import AppointmentSlots

class SLMService:
    def __init__(self):
        self.loader = SLMLoader()
        self.repository = MongoRepository()
        self.active_sessions = {}

    def load(self, model_name: str):
        return self.loader.load_model(model_name)

    def _update_slots(self, text: str, slots: AppointmentSlots):
        """Extraction manuelle par Regex (sécurité supplémentaire)"""
        text_l = text.lower()

        m = re.search(r"(?:my name is|i'm|i am)\s+([a-zA-Z]+)", text_l)
        if m:
            slots.username = m.group(1).capitalize()

        for s in ["dentist", "doctor", "haircut", "car repair", "plumbing"]:
            if s in text_l:
                slots.service = s.capitalize()

        for d in ["monday", "tuesday", "wednesday", "thursday", "friday"]:
            if d in text_l:
                slots.date = d.capitalize()

        times = re.findall(r'(\d{1,2}(?::\d{2})?\s*(?:am|pm))', text_l)
        if times:
            slots.heure = times[0].upper()

    def infer_with_memory(self, call_id: str, phone: str, user_input: str):
        try:
            if call_id not in self.active_sessions:
                self.active_sessions[call_id] = {
                    "slots": AppointmentSlots(),
                    "name_asked": False,
                    "confirmed": False,
                }

            session = self.active_sessions[call_id]
            slots = session["slots"]
            text_l = user_input.lower()

            # --- FONCTION UTILITAIRE POUR UN RETOUR UNIFORME ---
            def format_response(message, is_complete=False, metrics=None):
                return {
                    "message": message,
                    "data": slots.model_dump(), # JSON des slots pour Calendar
                    "is_complete": is_complete,
                    "metrics": metrics
                }

            # --- GARDE 0 : Annulation ---
            if any(w in text_l for w in ["cancel", "never mind", "forget it"]):
                msg = "No problem, I've cancelled that request. Anything else I can help with?"
                self._log_turn(call_id, phone, session, user_input, msg)
                self.active_sessions.pop(call_id, None)
                return format_response(msg)

            # --- GARDE CLOTURE ---
            if session["confirmed"] and any(
                w in text_l for w in ["no", "that's all", "thank you", "thanks", "bye", "goodbye", "nothing else"]
            ):
                msg = "You're welcome! Have a great day, goodbye!"
                self._log_turn(call_id, phone, session, user_input, msg)
                self.active_sessions.pop(call_id, None)
                return format_response(msg)

            # Mise à jour des slots via Regex avant d'appeler l'IA
            self._update_slots(user_input, slots)

            # --- GARDE 1 : Demander le nom ---
            if slots.service and slots.date and slots.heure and not slots.username:
                if not session["name_asked"]:
                    session["name_asked"] = True
                    msg = "Perfect. What name should I put this reservation under?"
                else:
                    msg = "Sorry, I didn't catch your name. Could you tell me your name please?"
                
                self._log_turn(call_id, phone, session, user_input, msg)
                return format_response(msg)

            # --- GARDE 2 : Confirmation finale ---
            if slots.service and slots.date and slots.heure and slots.username and not session["confirmed"]:
                session["confirmed"] = True
                msg = (f"Perfect. I've updated your appointment at {slots.lieu}. "
                       f"It's now set for a {slots.service} on {slots.date} at {slots.heure}. Anything else?")
                self._log_turn(call_id, phone, session, user_input, msg)
                return format_response(msg, is_complete=True)

            # --- APPEL À L'IA POUR EXTRACTION JSON ---
            system_prompt = (
                "You are a professional booking assistant. You MUST respond ONLY in valid JSON format.\n"
                "Structure: {\"message\": \"your voice reply\", \"data\": {\"username\": \"...\", \"date\": \"...\", \"heure\": \"...\", \"service\": \"...\"}}\n"
                f"CURRENT DATA STATE: {slots.model_dump_json()}"
            )

            result = self.loader.generate(system_prompt, user_input)
            if "error" in result:
                return result

            try:
                # Extraction robuste du JSON (au cas où le modèle ajoute du texte autour)
                raw_res = result["response"]
                start_idx = raw_res.find('{')
                end_idx = raw_res.rfind('}') + 1
                
                if start_idx != -1 and end_idx > 0:
                    ai_data = json.loads(raw_res[start_idx:end_idx])
                else:
                    # Si pas d'accolades, on traite comme du texte pur
                    ai_data = {"message": raw_res, "data": {}}

                # Mise à jour des slots (le reste de ton code est bon...)
                extracted = ai_data.get("data", {})
                if extracted.get("username"): slots.username = extracted["username"]
                if extracted.get("date"): slots.date = extracted["date"]
                if extracted.get("heure"): slots.heure = extracted["heure"]
                if extracted.get("service"): slots.service = extracted["service"]

                msg = ai_data.get("message", raw_res if not ai_data.get("message") else ai_data["message"])
                complete = all([slots.username, slots.date, slots.heure, slots.service])

                self._log_turn(call_id, phone, session, user_input, msg)
                return format_response(msg, is_complete=complete, metrics=result.get("consumption"))
            
            except json.JSONDecodeError:
                # Fallback si l'IA ne renvoie pas de JSON valide
                msg = result["response"]
                self._log_turn(call_id, phone, session, user_input, msg)
                return format_response(msg)

        except Exception as e:
            print(f"❌ Exception dans infer_with_memory: {e}")
            return {"error": f"INTERNAL_ERROR: {e}"}

    def _log_turn(self, call_id, phone, session, user_input, ai_response):
        turn_data = {
            "timestamp": time.time(),
            "user_prompt": user_input,
            "ai_response": ai_response,
        }
        self.repository.save_full_log(call_id, phone, session["slots"].model_dump(), turn_data)