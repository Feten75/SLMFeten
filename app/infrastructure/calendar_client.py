import requests
import dateparser
from datetime import datetime, timedelta

API_BASE_URL = "http://13.36.114.51:8004"
ENTREPRISE_ID = "6a671d9bb9aa73a07aa11110" 

class CalendarClient:
    def __init__(self):
        self.token = None 

    def _format_to_iso(self, day_text: str, time_text: str):
        """Convertit 'Monday' et '10 AM' en format ISO 8601 pour le Swagger."""
        try:
            combined = f"{day_text} {time_text}"
            dt = dateparser.parse(combined, settings={'PREFER_DATES_FROM': 'future'})
            
            if not dt:
                dt = datetime.now() + timedelta(days=1)
            
            # Format attendu par Swagger : 2025-01-01T10:00:00Z
            start_iso = dt.strftime("%Y-%m-%dT%H:%M:00Z")
            end_iso = (dt + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:00Z")
            return start_iso, end_iso
        except Exception as e:
            print(f"⚠️ Erreur parsing date: {e}")
            return "2025-01-01T10:00:00Z", "2025-01-01T11:00:00Z"

    def create_event(self, appointment_data: dict):
        endpoint = f"{API_BASE_URL}/google-calendar/create_CalendarEvent"
        
        params = {
            "entreprise_Id": ENTREPRISE_ID,
            "calendar_id": "primary",
            "check_busy": "false",
            "check_closing_hours": "false"
        }

        iso_start, iso_end = self._format_to_iso(
            appointment_data.get("date", ""), 
            appointment_data.get("heure", "")
        )

        payload = {
            "summary": f"RDV {appointment_data.get('service')} - {appointment_data.get('username')}",
            "description": f"Réservation automatique Echo Parrot pour {appointment_data.get('service')}",
            "start": iso_start,
            "end": iso_end,
            "timezone": "Europe/Paris",
            "attendees": []
        }
        
        try:
            print(f"Envoi au serveur {API_BASE_URL} ---")
            response = requests.post(endpoint, params=params, json=payload, timeout=10)
            
            if response.status_code in [200, 201]:
                print("RÉUSSITE : Événement créé dans le calendrier !")
                return response.json()
            else:
                print(f"Erreur API ({response.status_code}): {response.text}")
                return None
        except Exception as e:
            print(f"Erreur critique connexion CalendarClient: {e}")
            return None
        