from pydantic import BaseModel
from typing import Optional

class AppointmentSlots(BaseModel):
    username: Optional[str] = None
    date: Optional[str] = None
    heure: Optional[str] = None
    service: Optional[str] = None
    lieu: Optional[str] = "City Center"

    def to_string(self):
        return (f"Status - Service: {self.service or 'missing'}, "
                f"Day: {self.date or 'missing'}, "
                f"Time: {self.heure or 'missing'}, "
                f"Client Name: {self.username or 'missing'}")