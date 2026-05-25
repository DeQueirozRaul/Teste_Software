from datetime import datetime, timedelta

import pytest

from backend.api import criar_app
from backend.database import init_db


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """Prepara uma execução ponta a ponta com banco novo."""
    monkeypatch.chdir(tmp_path)
    init_db()
    app = criar_app(tmp_path / "notas_fiscais.db")
    app.config["TESTING"] = True
    return app.test_client()


def test_e2e_login_cadastro_listagem_e_resumo(client):
    """Valida o fluxo completo de login, cadastro, consulta e resumo."""
    login = client.post(
        "/api/login",
        json={"username": "admin", "password": "admin"},
    )
    assert login.status_code == 200

    cadastro = client.post(
        "/api/notas",
        json={
            "data": "15/04/2026",
            "valor": "300.00",
            "estabelecimento": "Cliente Fluxo E2E",
            "categoria": "Venda",
            "tipo": "Entrada",
        },
    )
    assert cadastro.status_code == 201

    listagem = client.get("/api/notas?busca=Fluxo E2E")
    notas = listagem.get_json()
    assert listagem.status_code == 200
    assert len(notas) == 1
    assert notas[0]["estabelecimento"] == "Cliente Fluxo E2E"

    resumo = client.get("/api/resumo").get_json()
    assert resumo["entradas"] >= 300.00
    assert resumo["saldo"] == pytest.approx(resumo["entradas"] - resumo["saidas"])


def test_e2e_fluxo_bloqueia_nota_invalida(client):
    """Valida o fluxo de tentativa de cadastro inválido e nova consulta."""
    amanha = (datetime.now() + timedelta(days=1)).strftime("%d/%m/%Y")

    cadastro = client.post(
        "/api/notas",
        json={
            "data": amanha,
            "valor": "-10",
            "estabelecimento": "Cliente Inválido E2E",
            "categoria": "Venda",
            "tipo": "Entrada",
        },
    )
    assert cadastro.status_code == 400

    listagem = client.get("/api/notas?busca=Inválido E2E")
    assert listagem.status_code == 200
    assert listagem.get_json() == []
