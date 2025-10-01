# -*- coding: utf-8 -*-
"""question.ipynb

Updated version with bullet-point casual answers.
"""

from fastapi import APIRouter
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
import requests

# MongoDB setup (hardcoded)
MONGO_URI = "mongodb+srv://chatpdfxai_db_user:esfmQRoJQZpJ7if3@cluster0.xzatb0d.mongodb.net/chatpdf?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client["chatpdf"]
chats_collection = db["chats"]

# Gemini config (hardcoded)
GEMINI_API_KEY = "AIzaSyAYzx76osJSXZd61P15YHFbByolJ0j0Xo8"
MODEL_NAME = "gemini-2.5-flash"
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent"

router = APIRouter(prefix="/question", tags=["question"])


def enforce_bullet_format(text: str) -> str:
    """
    Ensure the answer is in bullet points even if Gemini misses formatting.
    """
    lines = text.split("\n")
    formatted = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if not line.startswith("-") and not line.startswith("•"):
            formatted.append(f"- {line}")
        else:
            formatted.append(line)
    return "\n".join(formatted)


@router.get("/ask")
def ask_question(chat_id: str, question: str, onlycontext: bool = True):
    chat = chats_collection.find_one({"_id": ObjectId(chat_id)})
    if not chat:
        return {"status": "no_answer", "answer": "Chat not found ❌"}

    context = chat["context"]

    if onlycontext:
        # STRICT: Answer only from context
        instruction = """
        You are a study assistant 📘🧠.
        RULES:
        • Answer ONLY from the CONTEXT given.
        • Use very simple and easy-to-understand language.
        • DO NOT add anything that is not in the CONTEXT.
        • If the answer is not in the CONTEXT, reply exactly:
          "❌ Sorry, I couldn’t find anything related in your uploads."
        """
    else:
        # Flexible: Casual + bullet points + explanations
        instruction = """
        You are a helpful and casual study buddy 📘😎.

        RULES:
        • Always answer in BULLET POINTS ✅
        • Use SUB-BULLETS if needed for examples or details.
        • Keep the tone casual (like explaining to a friend).
        • Add simple explanations so beginners also understand.
        • Use emojis naturally 🎯✨
        • Cover all parts of the question clearly.
        • If needed, you can go beyond the context and give extra helpful info.

        FORMAT:
        - Main idea
          - Sub point / example
          - Sub point / explanation
        """

    user_prompt = f"""
    {instruction}

    CONTEXT:
    {context}

    QUESTION:
    {question}
    """

    payload = {"contents": [{"role": "user", "parts": [{"text": user_prompt}]}]}
    headers = {"Content-Type": "application/json", "x-goog-api-key": GEMINI_API_KEY}

    try:
        response = requests.post(GEMINI_API_URL, json=payload, headers=headers, timeout=60)
        response.raise_for_status()
        data = response.json()

        if "candidates" in data and len(data["candidates"]) > 0:
            answer = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        else:
            answer = "❌ Sorry, I couldn’t find anything related."

        # Enforce bullet-point style if onlycontext = False
        if not onlycontext and not answer.startswith("❌"):
            answer = enforce_bullet_format(answer)

        # Save user question + AI answer in history
        chats_collection.update_one(
            {"_id": ObjectId(chat_id)},
            {"$push": {"messages": {"role": "user", "text": question, "timestamp": datetime.utcnow().isoformat()}}}
        )
        chats_collection.update_one(
            {"_id": ObjectId(chat_id)},
            {"$push": {"messages": {"role": "assistant", "text": answer, "timestamp": datetime.utcnow().isoformat()}}}
        )

        return {
            "status": "answer" if not answer.startswith("❌") else "no_answer",
            "answer": None if answer.startswith("❌") else answer,
        }
    except Exception as e:
        return {"status": "no_answer", "answer": f"API error: {str(e)}"}
