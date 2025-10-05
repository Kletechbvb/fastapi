# -*- coding: utf-8 -*-
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Import routers
from user import router as user_router
from chat import router as chat_router
from question import router as question_router

app = FastAPI(title="Study API", version="1.0")

# CORS Configuration - CRITICAL FOR FRONTEND INTEGRATION
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://claude.ai",
        "http://localhost:*",
        "http://127.0.0.1:*",
        "*"  # For development - replace with specific domains in production
    ],
    allow_credentials=False,  # Set to False when using "*" in origins
    allow_methods=["*"],  # Allow all methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allow all headers
    expose_headers=["*"]
)

# Health check
@app.get("/")
def health_check():
    return {"status": "ok", "message": "All routers are working 🚀"}

# Register routers
app.include_router(user_router)
app.include_router(chat_router)
app.include_router(question_router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
