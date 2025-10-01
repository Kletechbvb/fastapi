from fastapi import APIRouter, UploadFile, Form
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
import requests, docx, io

# MongoDB setup (hardcoded)
MONGO_URI = "mongodb+srv://chatpdfxai_db_user:esfmQRoJQZpJ7if3@cluster0.xzatb0d.mongodb.net/chatpdf?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client["chatpdf"]
chats_collection = db["chats"]

# OCR.space config (hardcoded)
OCR_API_KEY = "K85634264488957"
OCR_URL = "https://api.ocr.space/parse/image"
CHUNK_SIZE = 1024 * 1024  # 1MB chunks

router = APIRouter(prefix="/chat", tags=["chat"])


def extract_text_from_file(file: UploadFile) -> str:
    filename = file.filename.lower()

    if filename.endswith(".docx"):
        d = docx.Document(file.file)
        return "\n".join([p.text for p in d.paragraphs])

    elif filename.endswith(".txt"):
        try:
            return file.file.read().decode("utf-8")
        except UnicodeDecodeError:
            file.file.seek(0)
            return file.file.read().decode("latin-1")

    elif filename.endswith((".pdf", ".png", ".jpg", ".jpeg")):
        file.file.seek(0)
        file_bytes = file.file.read()
        text = ""

        # Split into 1MB chunks
        for i in range(0, len(file_bytes), CHUNK_SIZE):
            chunk = file_bytes[i:i+CHUNK_SIZE]

            # Send chunk to OCR.space
            response = requests.post(
                OCR_URL,
                files={
                    "file": (
                        f"{file.filename}_part{i//CHUNK_SIZE+1}",
                        io.BytesIO(chunk),
                        file.content_type
                    )
                },
                data={"apikey": OCR_API_KEY, "language": "eng"}
            )

            result = response.json()

            if result.get("IsErroredOnProcessing"):
                text += f"\n❌ OCR failed on chunk {i//CHUNK_SIZE+1}: {result.get('ErrorMessage', 'Unknown error')}\n"
                continue

            for parsed_result in result.get("ParsedResults", []):
                text += parsed_result.get("ParsedText", "") + "\n"

        return text.strip()

    else:
        return "Unsupported file format."


@router.post("/create")
async def create_chat(user_email: str = Form(...), file: UploadFile = Form(...)):
    extracted_text = extract_text_from_file(file)

    chat_doc = {
        "user_email": user_email,
        "file_name": file.filename,
        "context": extracted_text,
        "messages": [],  # chat history
        "created_at": datetime.utcnow().isoformat()
    }
    result = chats_collection.insert_one(chat_doc)

    return {
        "status": "success",
        "chat_id": str(result.inserted_id),
        "context_preview": extracted_text[:200]
    }


@router.get("/history/{chat_id}")
def get_chat_history(chat_id: str):
    chat = chats_collection.find_one({"_id": ObjectId(chat_id)}, {"messages": 1, "file_name": 1})
    if not chat:
        return {"status": "error", "message": "Chat not found ❌"}
    return {
        "status": "success",
        "file_name": chat["file_name"],
        "messages": chat.get("messages", [])
    }


@router.get("/getall")
def get_all_chats(user_email: str):
    chats = chats_collection.find({"user_email": user_email}, {"file_name": 1, "created_at": 1})
    result = [
        {"chat_id": str(c["_id"]), "file_name": c["file_name"], "created_at": c.get("created_at")}
        for c in chats
    ]
    return {"status": "success", "chats": result}


@router.delete("/delete/{chat_id}")
def delete_chat(chat_id: str, user_email: str):
    chat = chats_collection.find_one({"_id": ObjectId(chat_id)})
    if not chat:
        return {"status": "error", "message": "Chat not found ❌"}

    # Only allow owner to delete
    if chat["user_email"] != user_email:
        return {"status": "error", "message": "Not authorized to delete this chat ❌"}

    chats_collection.delete_one({"_id": ObjectId(chat_id)})
    return {"status": "success", "message": f"Chat {chat_id} deleted ✅"}
