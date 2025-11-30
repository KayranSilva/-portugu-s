# -*- coding: utf-8 -*-
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

# ========== AUTH ==========

class SignupIn(BaseModel):
    name: str
    email: EmailStr
    password: str

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class AuthOut(BaseModel):
    message: str
    token: str
    user_id: int
    user_name: str
    user_email: str

class MeOut(BaseModel):
    user_id: int
    user_name: str
    user_email: str

# ========== QUESTIONS ==========

class QuestionCreate(BaseModel):
    tipo: str  # 'fechada' ou 'aberta'
    titulo: str
    enunciado: str
    alternativas: Optional[List[str]] = None
    gabarito: Optional[str] = None
    resposta_esperada: Optional[str] = None
    filtro_principal: Optional[str] = None
    dificuldade: Optional[str] = None
    subgenero: Optional[str] = None
    fonte_nome: Optional[str] = None
    fonte_ano: Optional[int] = None
    image_url: Optional[str] = None
    # ❗ NÃO colocamos owner_id aqui: ele vem do usuário logado no backend.

class QuestionUpdate(BaseModel):
    tipo: Optional[str] = None
    titulo: Optional[str] = None
    enunciado: Optional[str] = None
    alternativas: Optional[List[str]] = None
    gabarito: Optional[str] = None
    resposta_esperada: Optional[str] = None
    filtro_principal: Optional[str] = None
    dificuldade: Optional[str] = None
    subgenero: Optional[str] = None
    fonte_nome: Optional[str] = None
    fonte_ano: Optional[int] = None
    image_url: Optional[str] = None
    # idem: nada de owner_id aqui, para não deixarmos o cliente mudar o dono.

class QuestionOut(BaseModel):
    id: int
    owner_id: int  # 🔐 agora aparece no output
    tipo: str
    titulo: str
    enunciado: str
    alternativas: Optional[List[str]] = None
    gabarito: Optional[str] = None
    resposta_esperada: Optional[str] = None
    filtro_principal: Optional[str] = None
    dificuldade: Optional[str] = None
    subgenero: Optional[str] = None
    fonte_nome: Optional[str] = None
    fonte_ano: Optional[int] = None
    image_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True  # se estiver em Pydantic v1, use: orm_mode = True

class RenameCategoryIn(BaseModel):
    old_name: str
    new_name: str
