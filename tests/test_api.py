import os
import sys
from importlib import reload
from pathlib import Path

from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def build_test_client(tmp_path: Path) -> TestClient:
    """
    Cria um TestClient isolando a base SQLite em um arquivo temporário.
    """
    os.environ["DATABASE_URL"] = f"sqlite:///{tmp_path / 'test.db'}"

    # Recarrega módulos que dependem do engine para usar o novo banco
    from backend.app import database, models, auth, questions, main

    for module in (database, models, auth, questions, main):
        reload(module)

    return TestClient(main.app)


def test_healthcheck(tmp_path):
    client = build_test_client(tmp_path)

    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_auth_and_question_flow(tmp_path):
    client = build_test_client(tmp_path)

    # signup
    signup_payload = {
        "name": "Test User",
        "email": "test_user@example.com",
        "password": "StrongPass1",
    }
    signup_resp = client.post("/auth/signup", json=signup_payload)
    assert signup_resp.status_code == 201
    token = signup_resp.json()["token"]

    headers = {"Authorization": f"Bearer {token}"}

    # verificar /auth/me
    me_resp = client.get("/auth/me", headers=headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["user_email"] == signup_payload["email"]

    # criar questão fechada mínima
    question_payload = {
        "tipo": "fechada",
        "titulo": "Questão teste",
        "enunciado": "Qual é a capital do Brasil?",
        "alternativas": ["Rio de Janeiro", "Brasília"],
        "gabarito": "B",
    }
    create_resp = client.post("/questions/", json=question_payload, headers=headers)
    assert create_resp.status_code == 201
    question = create_resp.json()

    # listar questões do usuário
    list_resp = client.get("/questions/", headers=headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1
    assert list_resp.json()[0]["id"] == question["id"]

    # deletar questão
    delete_resp = client.delete(f"/questions/{question['id']}", headers=headers)
    assert delete_resp.status_code == 204
