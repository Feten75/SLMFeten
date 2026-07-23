import time
import re
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

            # --- GARDE 0 : annulation explicite ---
            if any(w in text_l for w in ["cancel", "never mind", "forget it"]):
                forced_reply = "No problem, I've cancelled that request. Anything else I can help with?"
                self._log_turn(call_id, phone, session, user_input, forced_reply)
                self.active_sessions.pop(call_id, None)
                return {"response": forced_reply}

            # --- GARDE CLOTURE : si déjà confirmé et l'utilisateur clôt la conversation ---
            if session["confirmed"] and any(
                w in text_l for w in ["no", "that's all", "thank you", "thanks", "bye", "goodbye", "nothing else"]
            ):
                forced_reply = "You're welcome! Have a great day, goodbye!"
                self._log_turn(call_id, phone, session, user_input, forced_reply)
                self.active_sessions.pop(call_id, None)  # fin de session
                return {"response": forced_reply}

            self._update_slots(user_input, slots)

            # --- GARDE 1 : demander le nom si manquant ---
            if slots.service and slots.date and slots.heure and not slots.username:
                if not session["name_asked"]:
                    session["name_asked"] = True
                    forced_reply = "Perfect. What name should I put this reservation under?"
                    self._log_turn(call_id, phone, session, user_input, forced_reply)
                    return {"response": forced_reply}
                else:
                    forced_reply = "Sorry, I didn't catch your name. Could you tell me your name please?"
                    self._log_turn(call_id, phone, session, user_input, forced_reply)
                    return {"response": forced_reply}

            # --- GARDE 2 : confirmer une seule fois ---
            if slots.service and slots.date and slots.heure and slots.username and not session["confirmed"]:
                session["confirmed"] = True
                forced_reply = (
                    f"Perfect. I've updated your appointment at {slots.lieu}. "
                    f"It's now set for a {slots.service} on {slots.date} at {slots.heure}. Anything else?"
                )
                self._log_turn(call_id, phone, session, user_input, forced_reply)
                return {"response": forced_reply}

            # --- GARDE 3 : déjà confirmé, l'utilisateur redemande un changement (jour/heure différents) ---
            if session["confirmed"]:
                # _update_slots a peut-être changé jour/heure au-dessus -> on renvoie la nouvelle confirmation
                forced_reply = (
                    f"Perfect. I've updated your appointment at {slots.lieu}. "
                    f"It's now set for a {slots.service} on {slots.date} at {slots.heure}. Anything else?"
                )
                self._log_turn(call_id, phone, session, user_input, forced_reply)
                return {"response": forced_reply}

            system_prompt = (
                "You are a professional assistant. Follow these steps exactly:\n"
                "1. Identify the service.\n"
                "2. If day/time are missing, ask for them.\n"
                f"CURRENT DATA: {slots.to_string()}"
            )

            result = self.loader.generate(system_prompt, user_input)
            if "error" in result:
                return result

            self._log_turn(call_id, phone, session, user_input, result["response"])
            return result

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
        