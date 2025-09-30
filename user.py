from fastapi import APIRouter
from pydantic import BaseModel
from pymongo import MongoClient
import hashlib

# MongoDB setup (hardcoded)
MONGO_URI = "mongodb+srv://chatpdfxai_db_user:esfmQRoJQZpJ7if3@cluster0.xzatb0d.mongodb.net/chatpdf?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client["chatpdf"]
users_collection = db["users"]

router = APIRouter(prefix="/user", tags=["user"])

class UserRegister(BaseModel):
    email: str
    password: str

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

@router.post("/register")
def register_user(user: UserRegister):
    if users_collection.find_one({"email": user.email}):
        return {"status": "error", "message": "User already exists"}
    
    users_collection.insert_one({
        "email": user.email,
        "password": hash_password(user.password)
    })
    return {"status": "success", "message": "User registered ✅"}

@router.post("/login")
def login_user(user: UserRegister):
    u = users_collection.find_one({"email": user.email})
    if not u or u["password"] != hash_password(user.password):
        return {"status": "error", "message": "Invalid credentials"}
    return {"status": "success", "message": "Login successful ✅"}
