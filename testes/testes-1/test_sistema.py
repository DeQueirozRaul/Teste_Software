import pytest
from datetime import datetime, timedelta
from app import data_para_db, data_para_ui, validar_data_emissao, validar_valor_nota, calcular_resumo_financeiro

def test_conversao_data_para_banco():
    assert data_para_db("15/03/2026") == "2026-03-15"

def test_conversao_data_banco_para_ui():
    assert data_para_ui("2026-03-15") == "15/03/2026"

def test_validar_data_emissao_formato_invalido():
    assert validar_data_emissao("31/02/2026") == False
    assert validar_data_emissao("texto_aleatorio") == False

def test_validar_valor_nota_formato_valido():
    assert validar_valor_nota("150.50") == True
    assert validar_valor_nota("2000,00") == True

def test_validar_data_futura_rejeitada():
    amanha = (datetime.now() + timedelta(days=1)).strftime('%d/%m/%Y')
    assert validar_data_emissao(amanha) == False, "O sistema não deve aceitar datas no futuro!"

def test_validar_valor_negativo_ou_zero_rejeitado():
    assert validar_valor_nota("-150.00") == False, "O sistema não deve aceitar valores negativos."
    assert validar_valor_nota("0.00") == False, "O sistema não deve aceitar notas com valor zero."

def test_resumo_financeiro_correto():
    registros_mock = [
        (1, '2026-04-01', 5000.00, 'Cliente A', 'Venda', 'Entrada', ''),
        (2, '2026-04-02', 1500.00, 'Fornecedor B', 'Estoque', 'Saída', ''),
        (3, '2026-04-03', 200.00, 'Energia', 'Despesa', 'Saída', '')
    ]
    resumo = calcular_resumo_financeiro(registros_mock)
    assert resumo['entradas'] == 5000.00, "O total de entradas deve somar apenas registros do tipo 'Entrada'"
    assert resumo['saidas'] == 1700.00, "O total de saídas deve somar apenas registros do tipo 'Saída'"
    assert resumo['saldo'] == 3300.00, "O saldo deve ser Entradas menos Saídas"