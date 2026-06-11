# init_db.py
from app.core.auth_handler import hash_password
from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017")
db = client["slm_database"]

# Création du compte feten
admin_user = {
    "username": "feten",
    "password": hash_password("Fatoyunadridi123="),
    "role": "ADMIN",
    "email": "admin@slm.com"
}

if not db.users.find_one({"username": "feten"}):
    db.users.insert_one(admin_user)
    print("Compte Admin 'feten' créé avec succès !")
else:
    print("L'admin existe déjà.")
##compte user:
#user
#user1@gmail.com
