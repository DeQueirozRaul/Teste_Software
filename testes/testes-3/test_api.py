from datetime import datetime, timedelta

import pytest

from backend.api import criar_app
from backend.database import init_db


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """Cria um cliente HTTP de teste com banco isolado."""
    monkeypatch.chdir(tmp_path)
    init_db()
    app = criar_app(tmp_path / "notas_fiscais.db")
    app.config["TESTING"] = True
    return app.test_client()


def test_api_login_admin_com_credenciais_validas(client):
    """Garante autenticação do usuário padrão criado no banco."""
    resposta = client.post(
        "/api/login",
        json={"username": "admin", "password": "admin"},
    )
    assert resposta.status_code == 200
    assert resposta.get_json()["username"] == "admin"


def test_api_login_rejeita_credenciais_invalidas(client):
    """Garante que credenciais incorretas sejam recusadas."""
    resposta = client.post(
        "/api/login",
        json={"username": "admin", "password": "senha_errada"},
    )
    assert resposta.status_code == 401


def test_api_lista_notas_populadas_no_banco(client):
    """Garante que a API liste as notas fiscais iniciais."""
    resposta = client.get("/api/notas")
    assert resposta.status_code == 200
    assert len(resposta.get_json()) > 0


def test_api_filtra_notas_por_texto(client):
    """Garante filtro de notas por estabelecimento ou categoria."""
    resposta = client.get("/api/notas?busca=Venda")
    dados = resposta.get_json()
    assert resposta.status_code == 200
    assert len(dados) > 0
    assert all(
        "Venda" in nota["categoria"]
        or "Venda" in nota["estabelecimento"]
        or "Venda" in nota["descricao"]
        for nota in dados
    )


def test_api_cria_nota_valida(client):
    """Garante cadastro de nota válida pela API."""
    resposta = client.post(
        "/api/notas",
        json={
            "data": "10/04/2026",
            "valor": "150,50",
            "estabelecimento": "Cliente API",
            "categoria": "Venda",
            "tipo": "Entrada",
        },
    )
    assert resposta.status_code == 201
    assert "id" in resposta.get_json()


def test_api_rejeita_nota_com_data_futura(client):
    """Garante rejeição de emissão futura pela API."""
    amanha = (datetime.now() + timedelta(days=1)).strftime("%d/%m/%Y")
    resposta = client.post(
        "/api/notas",
        json={
            "data": amanha,
            "valor": "150,50",
            "estabelecimento": "Cliente Futuro",
            "categoria": "Venda",
            "tipo": "Entrada",
        },
    )
    assert resposta.status_code == 400


def test_api_rejeita_nota_com_valor_zero(client):
    """Garante rejeição de nota sem valor financeiro."""
    resposta = client.post(
        "/api/notas",
        json={
            "data": "10/04/2026",
            "valor": "0",
            "estabelecimento": "Cliente Zero",
            "categoria": "Venda",
            "tipo": "Entrada",
        },
    )
    assert resposta.status_code == 400


def test_api_resumo_retorna_totais_financeiros(client):
    """Garante que o resumo da API exponha entradas, saídas e saldo."""
    resposta = client.get("/api/resumo")
    resumo = resposta.get_json()
    assert resposta.status_code == 200
    assert resumo["entradas"] > 0
    assert resumo["saidas"] > 0
    assert resumo["saldo"] == pytest.approx(resumo["entradas"] - resumo["saidas"])
