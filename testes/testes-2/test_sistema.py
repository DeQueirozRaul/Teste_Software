import sqlite3
from datetime import datetime, timedelta

import pytest

from app import (
    calcular_resumo_financeiro,
    data_para_db,
    data_para_ui,
    validar_data_emissao,
    validar_valor_nota,
)
from backend.database import init_db


def buscar_um(db_path, query, params=()):
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(query, params).fetchone()
    finally:
        conn.close()


def buscar_todos(db_path, query):
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(query).fetchall()
    finally:
        conn.close()


def test_01_converte_data_ui_para_banco():
    """Garante que uma data válida da interface seja convertida para ISO."""
    assert data_para_db("15/03/2026") == "2026-03-15"


def test_02_data_ui_invalida_retorna_none():
    """Garante que datas impossíveis não sejam gravadas no banco."""
    assert data_para_db("31/02/2026") is None


def test_03_converte_data_banco_para_ui():
    """Garante que uma data ISO seja exibida no formato brasileiro."""
    assert data_para_ui("2026-03-15") == "15/03/2026"


def test_04_data_banco_invalida_eh_preservada_na_ui():
    """Garante que valores inesperados não quebrem a exibição."""
    assert data_para_ui("data_invalida") == "data_invalida"


def test_05_validar_data_emissao_aceita_data_atual():
    """Garante que uma nota emitida hoje seja aceita."""
    hoje = datetime.now().strftime("%d/%m/%Y")
    assert validar_data_emissao(hoje) is True


def test_06_validar_data_emissao_aceita_data_passada():
    """Garante que uma nota já emitida no passado seja aceita."""
    assert validar_data_emissao("01/01/2026") is True


def test_07_validar_data_emissao_rejeita_data_futura():
    """Garante que o sistema bloqueie notas emitidas no futuro."""
    amanha = (datetime.now() + timedelta(days=1)).strftime("%d/%m/%Y")
    assert validar_data_emissao(amanha) is False


def test_08_validar_data_emissao_rejeita_data_invalida():
    """Garante que datas inexistentes sejam rejeitadas."""
    assert validar_data_emissao("31/02/2026") is False


def test_09_validar_valor_nota_aceita_decimal_com_virgula():
    """Garante que valores decimais com vírgula sejam aceitos."""
    assert validar_valor_nota("2000,00") is True


def test_10_validar_valor_nota_aceita_decimal_com_ponto():
    """Garante que valores decimais com ponto sejam aceitos."""
    assert validar_valor_nota("150.50") is True


def test_11_validar_valor_nota_rejeita_valor_negativo():
    """Garante que notas com valor negativo sejam bloqueadas."""
    assert validar_valor_nota("-150.00") is False


def test_12_validar_valor_nota_rejeita_zero():
    """Garante que notas sem valor financeiro sejam bloqueadas."""
    assert validar_valor_nota("0.00") is False


def test_13_resumo_financeiro_sem_registros_fica_zerado():
    """Garante totais zerados quando não há notas cadastradas."""
    assert calcular_resumo_financeiro([]) == {
        "entradas": 0.0,
        "saidas": 0.0,
        "saldo": 0.0,
    }


def test_14_resumo_financeiro_soma_apenas_entradas():
    """Garante que entradas sejam acumuladas no total correto."""
    registros = [
        (1, "2026-04-01", 100.0, "Cliente A", "Venda", "Entrada", ""),
        (2, "2026-04-02", 250.0, "Cliente B", "Venda", "Entrada", ""),
    ]
    resumo = calcular_resumo_financeiro(registros)
    assert resumo["entradas"] == 350.0
    assert resumo["saidas"] == 0.0
    assert resumo["saldo"] == 350.0


def test_15_resumo_financeiro_soma_apenas_saidas():
    """Garante que saídas sejam acumuladas no total correto."""
    registros = [
        (1, "2026-04-01", 80.0, "Fornecedor A", "Despesa", "Saída", ""),
        (2, "2026-04-02", 20.0, "Fornecedor B", "Despesa", "Saída", ""),
    ]
    resumo = calcular_resumo_financeiro(registros)
    assert resumo["entradas"] == 0.0
    assert resumo["saidas"] == 100.0
    assert resumo["saldo"] == -100.0


def test_16_resumo_financeiro_preserva_centavos():
    """Garante que os cálculos financeiros mantenham centavos."""
    registros = [
        (1, "2026-04-01", 10.75, "Cliente A", "Venda", "Entrada", ""),
        (2, "2026-04-02", 4.25, "Fornecedor B", "Despesa", "Saída", ""),
    ]
    resumo = calcular_resumo_financeiro(registros)
    assert resumo["entradas"] == pytest.approx(10.75)
    assert resumo["saidas"] == pytest.approx(4.25)
    assert resumo["saldo"] == pytest.approx(6.50)


def test_17_init_db_cria_arquivo_sqlite(tmp_path, monkeypatch):
    """Garante que a inicialização crie o arquivo do banco local."""
    monkeypatch.chdir(tmp_path)
    init_db()
    assert (tmp_path / "notas_fiscais.db").exists()


def test_18_init_db_cria_tabelas_necessarias(tmp_path, monkeypatch):
    """Garante que as tabelas usuarios e notas existam no banco."""
    monkeypatch.chdir(tmp_path)
    init_db()
    tabelas = buscar_todos(
        tmp_path / "notas_fiscais.db",
        "SELECT name FROM sqlite_master WHERE type='table'",
    )
    assert ("usuarios",) in tabelas
    assert ("notas",) in tabelas


def test_19_init_db_cadastra_usuario_admin(tmp_path, monkeypatch):
    """Garante que o usuário padrão admin/admin seja criado."""
    monkeypatch.chdir(tmp_path)
    init_db()
    usuario = buscar_um(
        tmp_path / "notas_fiscais.db",
        "SELECT username, password FROM usuarios WHERE username = ?",
        ("admin",),
    )
    assert usuario == ("admin", "admin")


def test_20_init_db_eh_idempotente(tmp_path, monkeypatch):
    """Garante que executar a inicialização duas vezes não duplique dados."""
    monkeypatch.chdir(tmp_path)
    init_db()
    total_notas_primeira_execucao = buscar_um(
        tmp_path / "notas_fiscais.db", "SELECT COUNT(*) FROM notas"
    )
    init_db()
    total_usuarios = buscar_um(
        tmp_path / "notas_fiscais.db",
        "SELECT COUNT(*) FROM usuarios WHERE username = 'admin'",
    )
    total_notas = buscar_um(tmp_path / "notas_fiscais.db", "SELECT COUNT(*) FROM notas")
    assert total_usuarios == (1,)
    assert total_notas[0] > 0
    assert total_notas == total_notas_primeira_execucao
