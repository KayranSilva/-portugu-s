# -*- coding: utf-8 -*-
from sqlalchemy import Column, Integer, String, DateTime, func, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    email = Column(String(200), unique=True, index=True, nullable=False)
    password_hash = Column(String(200), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)

    # 🔐 Dono da questão
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    owner = relationship("User", backref="questions")

    # básicos
    tipo = Column(String(20), nullable=False)   # 'fechada' | 'aberta'
    titulo = Column(String(200), nullable=False)
    enunciado = Column(Text, nullable=False)

    # fechada
    alternativas = Column(JSON, nullable=True)  # lista de strings
    gabarito = Column(String(2), nullable=True) # 'A', 'B', ...

    # aberta
    resposta_esperada = Column(Text, nullable=True)

    # metadados (filtros)
    filtro_principal = Column(String(80), nullable=True)
    dificuldade = Column(String(20), nullable=True)
    subgenero = Column(String(80), nullable=True)
    fonte_nome = Column(String(200), nullable=True)
    fonte_ano = Column(Integer, nullable=True)

    # imagem
    image_url = Column(String(500), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
