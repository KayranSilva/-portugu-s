# -*- coding: utf-8 -*-
"""
Main application file para +Português
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

# Importar blueprints de rotas
from .auth import router as auth_router
from .questions import router as questions_router
from .database import Base, engine


# Criar tabelas no banco se não existirem
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="+Português API",
    description="API para gerenciamento de banco de questões",
    version="1.0.0"
)

# ==================== CORS ====================
allowed = os.environ.get("API_ALLOWED_ORIGINS")
if allowed:
    allow_origins = [o.strip() for o in allowed.split(",") if o.strip()]
else:
    # Valores seguros por padrão para desenvolvimento local
    allow_origins = [
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== STATIC FILES ====================
if not os.path.exists("static"):
    os.makedirs("static", exist_ok=True)

if not os.path.exists("static/uploads"):
    os.makedirs("static/uploads", exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")

# ==================== ROTAS ====================
app.include_router(auth_router)
app.include_router(questions_router)

# ==================== ROOT ====================
@app.get("/")
def read_root():
    return {
        "message": "+Português API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "auth": "/auth/signup, /auth/login, /auth/me",
            "questions": "/questions (GET, POST, DELETE, PUT)"
        }
    }

# ==================== HEALTH CHECK ====================
@app.get("/health")
def health_check():
    return {"status": "ok", "service": "+Português API"}
