from pymongo import MongoClient
from pymongo.errors import PyMongoError

class MongoRepository:
    def __init__(self):
        self.client = MongoClient("mongodb://localhost:27017", serverSelectionTimeoutMS=3000)
        self.db = self.client["slm_database"]
        self.users = self.db["users"]
        self.logs = self.db["logs"]
        self.conversations = self.db["full_conversation_slmv5"] 

    def find_by_username(self, username: str):
        return self.users.find_one({"username": username})

    def create_user(self, user_data: dict):
        return self.users.insert_one(user_data)

    def save(self, log_data: dict):
        try:
            return self.logs.insert_one(log_data)
        except PyMongoError as e:
            print(f"❌ Erreur MongoDB (save): {e}")
            return None

    def save_full_log(self, call_id: str, phone: str, slots_dict: dict, turn_data: dict):
        try:
            return self.conversations.update_one(
                {"call_id": call_id},
                {
                    "$set": {
                        "phone": phone,
                        "extracted_info": {
                            "username": slots_dict.get("username"),
                            "date": slots_dict.get("date"),
                            "time": slots_dict.get("heure"),
                            "service": slots_dict.get("service"),
                            "location": slots_dict.get("lieu"),
                        },
                        "last_update": turn_data["timestamp"],
                    },
                    "$push": {"conversation_history": turn_data},
                },
                upsert=True,
            )
        except PyMongoError as e:
            print(f"❌ Erreur MongoDB (save_full_log): {e}")
            return None
        