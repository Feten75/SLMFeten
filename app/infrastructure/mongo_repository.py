from pymongo import MongoClient

class MongoRepository:
    def __init__(self):
        # Connexion à MongoDB
        self.client = MongoClient("mongodb://localhost:27017")
        self.db = self.client["slm_database"]
        
        # Collection pour les utilisateurs
        self.users = self.db["users"]
        
        # Collection pour l'historique et les métriques (C'est ce qui manquait !)
        self.logs = self.db["logs"]

    def find_by_username(self, username: str):
        """Cherche un utilisateur par son pseudo"""
        return self.users.find_one({"username": username})

    def create_user(self, user_data: dict):
        """Crée un nouvel utilisateur"""
        return self.users.insert_one(user_data)

    def save(self, log_data: dict):
        """
        Enregistre les données d'inférence (réponse IA, temps, RAM, CPU)
        Cette méthode est appelée par SLMService.infer()
        """
        try:
            return self.logs.insert_one(log_data)
        except Exception as e:
            print(f"❌ Erreur lors de l'enregistrement dans MongoDB : {e}")
            return None