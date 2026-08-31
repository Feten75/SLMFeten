import time
import re
import json
from app.infrastructure.calendar_client import CalendarClient
from app.infrastructure.slm_loader import SLMLoader
from app.infrastructure.mongo_repository import MongoRepository
from app.domain.entities.appointment_memory import AppointmentSlots

class SLMService:
    def __init__(self):
        self.loader = SLMLoader()
        self.repository = MongoRepository()
        self.calendar = CalendarClient()
        self.active_sessions = {}

    def load(self, model_name: str):
        return self.loader.load_model(model_name)

    def _update_slots(self, text: str, slots: AppointmentSlots):
        text_l = text.lower()
        m = re.search(r"(?:my name is|i'm|i am|appelez moi|je suis)\s+([a-zA-Z]+)", text_l)
        if m: slots.username = m.group(1).capitalize()

        for s in ["dentist", "doctor", "haircut", "car repair", "plumbing"]:
            if s in text_l: slots.service = s.capitalize()

        for d in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
            if d in text_l: slots.date = d.capitalize()

        times = re.findall(r'(\d{1,2}(?::\d{2})?\s*(?:am|pm|h))', text_l)
        if times: slots.heure = times[0].upper()

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

            def format_response(message, is_complete=False, metrics=None):
                return {
                    "message": message,
                    "data": slots.model_dump(),
                    "is_complete": is_complete,
                    "metrics": metrics
                }

            if any(w in text_l for w in ["cancel", "never mind", "forget it", "annuler"]):
                msg = "No problem, I've cancelled that request."
                self._log_turn(call_id, phone, session, user_input, msg)
                self.active_sessions.pop(call_id, None)
                return format_response(msg, is_complete=True)

            if session["confirmed"] and any(
                w in text_l for w in ["no", "that's all", "thank you", "thanks", "bye", "nothing else"]
            ):
                msg = "You're welcome! Have a great day, goodbye!"
                self._log_turn(call_id, phone, session, user_input, msg)
                self.active_sessions.pop(call_id, None)
                return format_response(msg, is_complete=True)

            self._update_slots(user_input, slots)

            system_prompt = (
                "You are a professional booking assistant. Respond ONLY in valid JSON.\n"
                "Structure: {\"message\": \"...\", \"data\": {\"username\": \"...\", \"date\": \"...\", \"heure\": \"...\", \"service\": \"...\"}}\n"
                f"CURRENT DATA: {slots.model_dump_json()}"
            )

            ai_result = self.loader.generate(system_prompt, user_input)
            if "error" in ai_result: return ai_result

            try:
                raw_res = ai_result["response"]
                start_idx = raw_res.find('{')
                end_idx = raw_res.rfind('}') + 1
                if start_idx != -1:
                    ai_data = json.loads(raw_res[start_idx:end_idx])
                    extracted = ai_data.get("data", {})
                    for key in ["username", "date", "heure", "service"]:
                        if extracted.get(key) and extracted[key] != "...":
                            setattr(slots, key, extracted[key])
                    msg = ai_data.get("message", "I've noted that.")
                else:
                    msg = raw_res
            except:
                msg = ai_result["response"]

            if not (slots.service and slots.date and slots.heure):
                self._log_turn(call_id, phone, session, user_input, msg)
                return format_response(msg)

            if not slots.username:
                if not session["name_asked"]:
                    session["name_asked"] = True
                    msg = "Perfect. Under what name should I put this reservation?"
                else:
                    msg = "Could you please tell me your name for the booking?"
                self._log_turn(call_id, phone, session, user_input, msg)
                return format_response(msg)

            if all([slots.service, slots.date, slots.heure, slots.username]) and not session["confirmed"]:
                session["confirmed"] = True
                
                calendar_response = self.calendar.create_event(slots.model_dump())
                status_msg = "Your appointment is confirmed." if calendar_response else "I've noted it, but I have a sync issue."

                msg = (f"Perfect {slots.username}. Your {slots.service} is set for "
                       f"{slots.date} at {slots.heure}. {status_msg} Anything else?")
                
                self._log_turn(call_id, phone, session, user_input, msg)
                return format_response(msg, is_complete=True, metrics=ai_result.get("consumption"))

            self._log_turn(call_id, phone, session, user_input, msg)
            return format_response(msg, metrics=ai_result.get("consumption"))

        except Exception as e:
            print(f"❌ Erreur SLMService: {e}")
            return {"error": str(e)}

    def _log_turn(self, call_id, phone, session, user_input, ai_response):
        try:
            turn_data = {"timestamp": time.time(), "user_prompt": user_input, "ai_response": ai_response}
            self.repository.save_full_log(call_id, phone, session["slots"].model_dump(), turn_data)
        except Exception as e:
            print(f"⚠️ Log error: {e}")
            