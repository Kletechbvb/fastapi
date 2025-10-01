from fastapi import APIRouter, UploadFile, Form
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
import docx, io, asyncio, httpx
from pdf2image import convert_from_bytes

# MongoDB setup (hardcoded)
MONGO_URI = "mongodb+srv://chatpdfxai_db_user:esfmQRoJQZpJ7if3@cluster0.xzatb0d.mongodb.net/chatpdf?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client["chatpdf"]
chats_collection = db["chats"]

# OCR.space config (hardcoded)
OCR_API_KEY = "K85634264488957"
OCR_URL = "https://api.ocr.space/parse/image"

router = APIRouter(prefix="/chat", tags=["chat"])


async def ocr_image_page(session, buf: io.BytesIO, page_num: int) -> str:
    files = {"file": (f"page_{page_num}.png", buf, "image/png")}
    data = {"apikey": OCR_API_KEY, "language": "eng"}

    resp = await session.post(OCR_URL, files=files, data=data)
    result = resp.json()

    if result.get("IsErroredOnProcessing"):
        return f"\n❌ OCR failed on page {page_num}: {result.get('ErrorMessage', 'Unknown error')}\n"

    text = ""
    for parsed_result in result.get("ParsedResults", []):
        text += parsed_result.get("ParsedText", "") + "\n"
    return text


async def extract_text_from_file(file: UploadFile) -> str:
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

    elif filename.endswith(".pdf"):
        file.file.seek(0)
        pdf_bytes = file.file.read()

        # Convert each PDF page into an image
        pages = convert_from_bytes(pdf_bytes, dpi=200)
        tasks = []

        async with httpx.AsyncClient(timeout=None) as session:
            for idx, page in enumerate(pages, start=1):
                buf = io.BytesIO()
                page.save(buf, format="PNG")
                buf.seek(0)

                tasks.append(ocr_image_page(session, buf, idx))

            results = await asyncio.gather(*tasks)

        return "\n".join(results).strip()

    elif filename.endswith((".png", ".jpg", ".jpeg")):
        file.file.seek(0)
        async with httpx.AsyncClient(timeout=None) as session:
            files = {"file": (file.filename, file.file, file.content_type)}
            data = {"apikey": OCR_API_KEY, "language": "eng"}
            resp = await session.post(OCR_URL, files=files, data=data)
            result = resp.json()

            if result.get("IsErroredOnProcessing"):
                return f"❌ OCR failed: {result.get('ErrorMessage', 'Unknown error')}"

            text = ""
            for parsed_result in result.get("ParsedResults", []):
                text += parsed_result.get("ParsedText", "") + "\n"
            return text.strip()

    else:
        return "Unsupported file format."


@router.post("/create")
async def create_chat(user_email: str = Form(...), file: UploadFile = Form(...)):
    extracted_text = await extract_text_from_file(file)

    chat_doc = {
        "user_email": user_email,
        "file_name": file.filename,
        "context": extracted_text,
        "messages": [],
        "created_at": datetime.utcnow().isoformat()
    }
    result = chats_collection.insert_one(chat_doc)

    return {
        "status": "success",
        "chat_id": str(result.inserted_id),
        "context_preview": extracted_text[:200]  # preview only
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

    if chat["user_email"] != user_email:
        return {"status": "error", "message": "Not authorized to delete this chat ❌"}

    chats_collection.delete_one({"_id": ObjectId(chat_id)})
    return {"status": "success", "message": f"Chat {chat_id} deleted ✅"}
