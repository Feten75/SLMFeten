from pymongo import MongoClient
from datetime import datetime

class MongoRepository:
    def __init__(self):
        self.client = MongoClient("mongodb://localhost:27017")
        self.db = self.client["slm_database"]
        self.collection = self.db["db_ollama_v_final"]

    def save(self, data: dict):
        data["timestamp"] = datetime.utcnow()
        result = self.collection.insert_one(data)
        print(f"DOCUMENT ENREGISTRÉ DANS MONGO AVEC SUCCESS! ID: {result.inserted_id}")
        
                                                                  