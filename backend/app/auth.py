# -*- coding: utf-8 -*-
import os
import re
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from sqlalchemy import func
from passlib.hash import sha256_crypt
from jose import JWTError, jwt

from .database import get_db
from .models import User
from .schemas import SignupIn, LoginIn, AuthOut, MeOut

router = APIRouter(prefix="/auth", tags=["auth"])

# =========================
# CONFIGURAÇÕES JWT
# =========================

# Em produção, defina SECRET_KEY via variável de ambiente
SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-please-and-set-env")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
)  # padrão: 60 minutos


def validate_password(password: str):
    """
    Valida força da senha.
    Regras:
    - mínimo 8 caracteres
    - pelo menos 1 letra maiúscula
    - pelo menos 1 letra minúscula
    - pelo menos 1 dígito
    """
    errors = []

    if len(password) < 8:
        errors.append("mínimo 8 caracteres")
    if not re.search(r"[A-Z]", password):
        errors.append("uma letra maiúscula")
    if not re.search(r"[a-z]", password):
        errors.append("uma letra minúscula")
    if not re.search(r"\d", password):
        errors.append("um número")

    if errors:
        raise HTTPException(
            status_code=400,
            detail=f"Senha fraca. Necessário: {', '.join(errors)}",
        )


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Gera um JWT assinado com expiração.
    O campo "sub" deve conter o ID do usuário como string.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# =========================
# ENDPOINT: SIGNUP
# =========================

@router.post("/signup", response_model=AuthOut, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupIn, db: Session = Depends(get_db)):
    """
    Cadastro de novo usuário.
    - Normaliza e-mail e nome
    - Valida força da senha
    - Impede e-mail duplicado
    - Retorna token JWT + dados básicos
    """
    email = payload.email.strip().lower()
    name = payload.name.strip()

    # Validação de senha forte
    validate_password(payload.password)

    # Verifica se e-mail já existe
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="E-mail já cadastrado",
        )

    # Cria usuário
    user = User(
        name=name,
        email=email,
        password_hash=sha256_crypt.hash(payload.password),
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    # Gera token
    token = create_access_token({"sub": str(user.id)})

    return {
        "message": "Cadastro realizado com sucesso",
        "token": token,
        "user_id": user.id,
        "user_name": user.name,
        "user_email": user.email,
    }


# =========================
# ENDPOINT: LOGIN
# =========================

@router.post("/login", response_model=AuthOut)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    """
    Login de usuário.
    - Busca por e-mail (case-insensitive)
    - Valida senha com hash
    - Retorna token JWT + dados básicos
    """
    email = payload.email.strip().lower()

    user = (
        db.query(User)
        .filter(func.lower(User.email) == email)
        .first()
    )

    if not user or not sha256_crypt.verify(payload.password, user.password_hash):
        raise HTTPException(
            status_code=401,
            detail="Credenciais inválidas",
        )

    token = create_access_token({"sub": str(user.id)})

    return {
        "message": "Login realizado com sucesso",
        "token": token,
        "user_id": user.id,
        "user_name": user.name,
        "user_email": user.email,
    }


# =========================
# HELPER: OBTÉM USUÁRIO PELO HEADER AUTH
# =========================

def get_current_user_from_auth_header(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    """
    Lê o cabeçalho Authorization e retorna o usuário autenticado.

    Aceita:
    - "Bearer <token>"
    - "<token>" direto
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Cabeçalho Authorization ausente",
        )

    parts = authorization.split()

    # Só token
    if len(parts) == 1:
        token = parts[0]
    # "Bearer token" ou similar
    elif len(parts) >= 2:
        token = parts[1]
    else:
        raise HTTPException(
            status_code=401,
            detail="Cabeçalho Authorization inválido",
        )

    # Valida JWT
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        if sub is None:
            raise HTTPException(
                status_code=401,
                detail="Token inválido",
            )
        user_id = int(sub)
    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Token inválido ou expirado",
        )
    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Token inválido",
        )

    # Busca usuário
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Usuário não encontrado",
        )

    return user


# =========================
# ENDPOINT: ME
# =========================

@router.get("/me", response_model=MeOut)
def me(current_user=Depends(get_current_user_from_auth_header)):
    """
    Retorna dados do usuário autenticado com base no token enviado no header.
    """
    return {
        "user_id": current_user.id,
        "user_name": current_user.name,
        "user_email": current_user.email,
    }
