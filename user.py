from fastapi import APIRouter
from pydantic import BaseModel, EmailStr
from pymongo import MongoClient
import hashlib, random, time
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# ------------------ HARDCODED CONFIG ------------------
MONGO_URI = "mongodb+srv://chatpdfxai_db_user:esfmQRoJQZpJ7if3@cluster0.xzatb0d.mongodb.net/chatpdf?retryWrites=true&w=majority&appName=Cluster0"
SENDGRID_API_KEY = "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"  # YOUR KEY
MAIL_FROM = "mrsadiq471@gmail.com"
OTP_EXPIRY_SECONDS = 300  # 5 minutes

# ------------------ DATABASE ------------------
client = MongoClient(MONGO_URI)
db = client["chatpdf"]
users_collection = db["users"]

# ------------------ ROUTER ------------------
router = APIRouter(prefix="/user", tags=["user"])

# ------------------ MODELS ------------------
class UserRegister(BaseModel):
    email: EmailStr
    password: str

class OTPVerify(BaseModel):
    email: EmailStr
    otp: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

# ------------------ HELPERS ------------------
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def generate_otp(length=6) -> str:
    return ''.join([str(random.randint(0, 9)) for _ in range(length)])

def send_email(to_email: str, subject: str, body: str, html: str = None):
    message = Mail(
        from_email=MAIL_FROM,
        to_emails=to_email,
        subject=subject,
        plain_text_content=body,
        html_content=html or body
    )
    sg = SendGridAPIClient(SENDGRID_API_KEY)
    sg.send(message)

# ------------------ REGISTER ------------------
@router.post("/register")
def register_user(user: UserRegister):
    u = users_collection.find_one({"email": user.email})
    if u and u.get("verified"):
        return {"status": "error", "message": "User already exists"}
    
    otp = generate_otp()
    expiry = int(time.time()) + OTP_EXPIRY_SECONDS

    users_collection.update_one(
        {"email": user.email},
        {"$set": {
            "email": user.email,
            "password": hash_password(user.password),
            "otp": otp,
            "otp_expiry": expiry,
            "verified": False
        }},
        upsert=True
    )

    send_email(
        to_email=user.email,
        subject="RagNova - Verify your account",
        body=f"Your RagNova OTP is: {otp}. It will expire in 5 minutes.",
        html=f"<h3>Welcome to RagNova 🚀</h3><p>Your OTP is <b>{otp}</b></p><p>It expires in 5 minutes.</p>"
    )

    return {"status": "success", "message": "OTP sent to your email 📧"}

# ------------------ VERIFY OTP ------------------
@router.post("/verify-otp")
def verify_otp(data: OTPVerify):
    u = users_collection.find_one({"email": data.email})
    if not u:
        return {"status": "error", "message": "User not found"}
    
    if not u.get("otp") or not u.get("otp_expiry"):
        return {"status": "error", "message": "OTP not generated"}
    
    if int(time.time()) > u["otp_expiry"]:
        return {"status": "error", "message": "OTP expired ⏳. Please request a new one."}

    if u["otp"] != data.otp:
        return {"status": "error", "message": "Invalid OTP ❌"}

    users_collection.update_one(
        {"email": data.email},
        {"$set": {"verified": True}, "$unset": {"otp": "", "otp_expiry": ""}}
    )

    # Send welcome email
    send_email(
        to_email=data.email,
        subject="Welcome to RagNova 🎉",
        body="Your account has been successfully verified. Enjoy using RagNova!",
        html="<h2>🎉 Welcome to RagNova!</h2><p>Your account has been verified successfully.</p>"
    )

    return {"status": "success", "message": "Account verified ✅"}

# ------------------ RESEND OTP ------------------
@router.post("/resend-otp")
def resend_otp(data: OTPVerify):
    u = users_collection.find_one({"email": data.email})
    if not u:
        return {"status": "error", "message": "User not found"}
    if u.get("verified"):
        return {"status": "error", "message": "User already verified ✅"}

    new_otp = generate_otp()
    new_expiry = int(time.time()) + OTP_EXPIRY_SECONDS

    users_collection.update_one(
        {"email": data.email},
        {"$set": {"otp": new_otp, "otp_expiry": new_expiry}}
    )

    send_email(
        to_email=data.email,
        subject="RagNova - Resend OTP",
        body=f"Your new RagNova OTP is: {new_otp}. It will expire in 5 minutes.",
        html=f"<p>Your new OTP is <b>{new_otp}</b></p><p>It expires in 5 minutes.</p>"
    )

    return {"status": "success", "message": "New OTP sent 📧"}

# ------------------ LOGIN ------------------
@router.post("/login")
def login_user(user: UserLogin):
    u = users_collection.find_one({"email": user.email})
    if not u:
        return {"status": "error", "message": "User not found"}
    
    if not u.get("verified"):
        return {"status": "error", "message": "User not verified ❌. Please verify your email first."}
    
    if u["password"] != hash_password(user.password):
        return {"status": "error", "message": "Invalid credentials ❌"}

    return {"status": "success", "message": f"Welcome back to RagNova, {user.email} 🎉"}
