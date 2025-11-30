# -*- coding: utf-8 -*-
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Request, status
from sqlalchemy.orm import Session
from sqlalchemy import func, case

from .database import get_db
from .models import Question
from .auth import get_current_user_from_auth_header
from .schemas import QuestionCreate, QuestionUpdate, QuestionOut, RenameCategoryIn

router = APIRouter(prefix="/questions", tags=["questions"])

# ==================== CATEGORIAS PADRÃO ====================

DEFAULT_CATEGORIES = [
    "Analise Linguistica",
    "Literatura",
    "Interpretacao Texto",
]

# ==================== UPLOAD DE IMAGEM ====================

@router.post("/upload-image")
def upload_image(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_from_auth_header),
):
    content_type = (file.content_type or "").lower()
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Arquivo não é uma imagem")

    max_size = 3 * 1024 * 1024  # 3MB

    contents = file.file.read()
    if len(contents) > max_size:
        raise HTTPException(status_code=413, detail="Arquivo muito grande. Máximo 3MB.")

    uploads_dir = Path("static") / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)

    original_suffix = Path(file.filename or "image").suffix or ".jpg"
    filename = f"{uuid.uuid4().hex}{original_suffix}"
    dest_path = uploads_dir / filename

    with dest_path.open("wb") as buffer:
        buffer.write(contents)

    file.file.close()

    base = str(request.base_url).rstrip("/")
    url = f"{base}/static/uploads/{filename}"
    return {"url": url, "filename": filename}

# ==================== CRIAR QUESTÃO ====================

@router.post("/", response_model=QuestionOut, status_code=status.HTTP_201_CREATED)
def create_question(
    payload: QuestionCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_from_auth_header),
):
    """Cria uma nova questão para o usuário autenticado."""

    if payload.tipo not in ["fechada", "aberta"]:
        raise HTTPException(status_code=400, detail="Tipo inválido")

    if not payload.titulo.strip():
        raise HTTPException(status_code=400, detail="Título não pode estar vazio")

    if not payload.enunciado.strip():
        raise HTTPException(status_code=400, detail="Enunciado não pode estar vazio")

    # validações para questão fechada
    if payload.tipo == "fechada":
        if not payload.alternativas or len(payload.alternativas) < 2:
            raise HTTPException(status_code=400, detail="Deve ter pelo menos 2 alternativas")
        if not payload.gabarito:
            raise HTTPException(status_code=400, detail="Gabarito é obrigatório")

    question = Question(
        tipo=payload.tipo,
        titulo=payload.titulo.strip(),
        enunciado=payload.enunciado.strip(),
        alternativas=payload.alternativas if payload.tipo == "fechada" else None,
        gabarito=payload.gabarito if payload.tipo == "fechada" else None,
        resposta_esperada=payload.resposta_esperada if payload.tipo == "aberta" else None,
        filtro_principal=payload.filtro_principal,
        dificuldade=payload.dificuldade,
        subgenero=payload.subgenero,
        fonte_nome=payload.fonte_nome,
        fonte_ano=payload.fonte_ano,
        image_url=payload.image_url,
        owner_id=current_user.id,  # 🔐 associa ao dono
    )

    db.add(question)
    db.commit()
    db.refresh(question)
    return question

# ==================== LISTAR QUESTÕES ====================

@router.get("/", response_model=list[QuestionOut])
def list_questions(
    filtro_principal: str | None = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_from_auth_header),
):
    """
    Lista questões SOMENTE do usuário logado,
    com filtro opcional por categoria.
    """
    query = db.query(Question).filter(Question.owner_id == current_user.id)

    if filtro_principal:
        query = query.filter(Question.filtro_principal == filtro_principal)

    questions = query.order_by(Question.created_at.desc()).all()
    return questions

# ==================== CATEGORIAS DINÂMICAS ====================

@router.get("/categories", response_model=list[str])
def list_categories(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_from_auth_header),
):
    """Lista categorias do usuário atual + categorias padrão."""
    rows = (
        db.query(Question.filtro_principal)
        .filter(Question.owner_id == current_user.id)
        .filter(Question.filtro_principal.isnot(None))
        .filter(Question.filtro_principal != "")
        .distinct()
        .all()
    )

    usadas = {r[0] for r in rows}
    todas = sorted(usadas.union(DEFAULT_CATEGORIES))
    return todas

@router.get("/categories/stats")
def categories_stats(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_from_auth_header),
):
    """Estatísticas por categoria do usuário atual."""
    rows = (
        db.query(
            Question.filtro_principal.label("name"),
            func.count(Question.id).label("total"),
            func.sum(case((Question.tipo == "fechada", 1), else_=0)).label("fechadas"),
            func.sum(case((Question.tipo == "aberta", 1), else_=0)).label("abertas"),
        )
        .filter(Question.owner_id == current_user.id)
        .filter(Question.filtro_principal.isnot(None))
        .filter(Question.filtro_principal != "")
        .group_by(Question.filtro_principal)
        .all()
    )

    stats = {
        r.name: {
            "name": r.name,
            "total": int(r.total or 0),
            "fechadas": int(r.fechadas or 0),
            "abertas": int(r.abertas or 0),
        }
        for r in rows
    }

    for cat in DEFAULT_CATEGORIES:
        if cat not in stats:
            stats[cat] = {"name": cat, "total": 0, "fechadas": 0, "abertas": 0}

    return [stats[name] for name in sorted(stats)]

# ==================== OBTER QUESTÃO POR ID ====================

@router.get("/{question_id}", response_model=QuestionOut)
def get_question(
    question_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_from_auth_header),
):
    """Obtém uma questão específica do usuário logado."""
    question = (
        db.query(Question)
        .filter(Question.id == question_id, Question.owner_id == current_user.id)
        .first()
    )

    if not question:
        raise HTTPException(status_code=404, detail="Questão não encontrada")

    return question

# ==================== ATUALIZAR QUESTÃO ====================

@router.put("/{question_id}", response_model=QuestionOut)
def update_question(
    question_id: int,
    payload: QuestionUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_from_auth_header),
):
    """Atualiza uma questão do usuário logado."""

    question = (
        db.query(Question)
        .filter(Question.id == question_id, Question.owner_id == current_user.id)
        .first()
    )

    if not question:
        raise HTTPException(status_code=404, detail="Questão não encontrada")

    update_data = payload.dict(exclude_unset=True)

    # === Tratamento da imagem ===
    if "image_url" in update_data:
        new_url = update_data["image_url"]
        old_url = question.image_url

        # Remover imagem antiga
        if new_url is None and old_url:
            try:
                filename = old_url.split("/")[-1]
                file_path = Path("static") / "uploads" / filename
                if file_path.exists():
                    file_path.unlink()
            except Exception as e:
                print(f"Erro ao remover imagem antiga: {e}")
            question.image_url = None
            update_data.pop("image_url", None)

        # Substituir imagem
        elif new_url and new_url != old_url:
            if old_url:
                try:
                    filename = old_url.split("/")[-1]
                    file_path = Path("static") / "uploads" / filename
                    if file_path.exists():
                        file_path.unlink()
                except Exception as e:
                    print(f"Erro ao remover imagem antiga: {e}")

    # === Validações básicas ===
    if "tipo" in update_data and update_data["tipo"] not in ["fechada", "aberta"]:
        raise HTTPException(status_code=400, detail="Tipo inválido")

    if "titulo" in update_data and not update_data["titulo"].strip():
        raise HTTPException(status_code=400, detail="Título não pode estar vazio")

    if "enunciado" in update_data and not update_data["enunciado"].strip():
        raise HTTPException(status_code=400, detail="Enunciado não pode estar vazio")

    # === Validações específicas ===
    effective_tipo = update_data.get("tipo", question.tipo)
    if effective_tipo == "fechada":
        alternativas = update_data.get("alternativas", question.alternativas)
        if not alternativas or len(alternativas) < 2:
            raise HTTPException(status_code=400, detail="Deve ter pelo menos 2 alternativas")

        gabarito = update_data.get("gabarito", question.gabarito)
        if not gabarito:
            raise HTTPException(status_code=400, detail="Gabarito é obrigatório")

    for key, value in update_data.items():
        setattr(question, key, value)

    db.commit()
    db.refresh(question)
    return question

# ==================== DELETAR QUESTÃO ====================

@router.delete("/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_question(
    question_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_from_auth_header),
):
    """Deleta uma questão do usuário logado."""
    question = (
        db.query(Question)
        .filter(Question.id == question_id, Question.owner_id == current_user.id)
        .first()
    )

    if not question:
        raise HTTPException(status_code=404, detail="Questão não encontrada")

    if question.image_url:
        try:
            filename = question.image_url.split("/")[-1]
            file_path = Path("static") / "uploads" / filename
            if file_path.exists():
                file_path.unlink()
        except Exception as e:
            print(f"Erro ao deletar imagem: {e}")

    db.delete(question)
    db.commit()
    return None

# ==================== RENOMEAR CATEGORIA ====================

@router.put("/rename-category")
def rename_category(
    payload: RenameCategoryIn,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_from_auth_header),
):
    """Renomeia uma categoria para o usuário logado."""
    
    old_name = payload.old_name.strip()
    new_name = payload.new_name.strip()
    
    if not old_name or not new_name:
        raise HTTPException(status_code=400, detail="old_name e new_name são obrigatórios")
    
    if old_name == new_name:
        return {"message": "Nomes são iguais, nenhuma alteração foi feita"}
    
    # Buscar todas as questões do usuário com a categoria antiga
    questions = (
        db.query(Question)
        .filter(
            Question.owner_id == current_user.id,
            Question.filtro_principal == old_name
        )
        .all()
    )
    
    if not questions:
        raise HTTPException(status_code=404, detail="Nenhuma questão encontrada com esta categoria")
    
    # Atualizar todas as questões
    for question in questions:
        question.filtro_principal = new_name
    
    db.commit()
    
    return {
        "message": f"Categoria '{old_name}' renomeada para '{new_name}'",
        "updated_count": len(questions)
    }

