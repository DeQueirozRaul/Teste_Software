import json
import sqlite3
from datetime import datetime, timedelta

import pytest
from playwright.sync_api import expect, sync_playwright

from backend.api import nivel_eh_admin, serializar_nota, validar_dados_nota
from backend.services import (
    calcular_resumo_financeiro,
    data_para_db,
    data_para_ui,
    validar_data_emissao,
    validar_valor_nota,
)


# ============================================================
# TESTES UNITARIOS
# ============================================================


@pytest.mark.case(
    id="R4-UNIT-001",
    description="Validar conversão de datas entre formato da interface e formato do banco.",
    steps="Chamar data_para_db com data brasileira e data_para_ui com data ISO.",
    input_data='data_para_db("05/04/2026"); data_para_ui("2026-04-05")',
    expected_output='"2026-04-05" e "05/04/2026"',
    success_criteria="As duas conversões retornam exatamente os formatos esperados.",
)
def test_unit_conversao_bidirecional_de_datas():
    assert data_para_db("05/04/2026") == "2026-04-05"
    assert data_para_ui("2026-04-05") == "05/04/2026"


@pytest.mark.case(
    id="R4-UNIT-002",
    description="Validar rejeição de datas inexistentes e datas futuras.",
    steps="Enviar uma data impossível e uma data maior que a data atual.",
    input_data='"31/02/2026"; amanhã no formato DD/MM/YYYY',
    expected_output="False para as duas validações",
    success_criteria="Datas inválidas ou futuras não são aceitas para emissão de nota.",
)
def test_unit_validacao_rejeita_datas_invalidas_e_futuras():
    amanha = (datetime.now() + timedelta(days=1)).strftime("%d/%m/%Y")
    assert validar_data_emissao("31/02/2026") is False
    assert validar_data_emissao(amanha) is False


@pytest.mark.case(
    id="R4-UNIT-003",
    description="Validar valores monetários positivos aceitos com ponto ou vírgula.",
    steps="Chamar validar_valor_nota com valores positivos em formatos usuais.",
    input_data='"199,90"; "199.90"',
    expected_output="True para os dois valores",
    success_criteria="O sistema aceita centavos com vírgula e ponto decimal.",
)
def test_unit_valor_positivo_aceita_virgula_e_ponto():
    assert validar_valor_nota("199,90") is True
    assert validar_valor_nota("199.90") is True


@pytest.mark.case(
    id="R4-UNIT-004",
    description="Validar bloqueio de valor zero, negativo e texto não numérico.",
    steps="Chamar validar_valor_nota com entradas financeiras inválidas.",
    input_data='"0"; "-10"; "abc"',
    expected_output="False para todas as entradas",
    success_criteria="Nenhuma entrada sem valor financeiro positivo é aceita.",
)
def test_unit_valor_invalido_rejeita_zero_negativo_e_texto():
    assert validar_valor_nota("0") is False
    assert validar_valor_nota("-10") is False
    assert validar_valor_nota("abc") is False


@pytest.mark.case(
    id="R4-UNIT-005",
    description="Validar cálculo financeiro com entradas e saídas misturadas.",
    steps="Enviar uma lista de registros para calcular_resumo_financeiro.",
    input_data="Entradas: 100.00 e 50.55; Saídas: 30.10 e 20.00",
    expected_output="entradas=150.55; saidas=50.10; saldo=100.45",
    success_criteria="Os totais preservam centavos e classificam Entrada/Saída corretamente.",
)
def test_unit_resumo_financeiro_calcula_totais_com_centavos():
    registros = [
        (1, "2026-04-01", 100.00, "Cliente A", "Venda", "Entrada", "", ""),
        (2, "2026-04-02", 30.10, "Fornecedor B", "Despesa", "Saída", "", ""),
        (3, "2026-04-03", 50.55, "Cliente C", "Venda", "Entrada", "", ""),
        (4, "2026-04-04", 20.00, "Fornecedor D", "Despesa", "Saída", "", ""),
    ]
    resumo = calcular_resumo_financeiro(registros)
    assert resumo["entradas"] == pytest.approx(150.55)
    assert resumo["saidas"] == pytest.approx(50.10)
    assert resumo["saldo"] == pytest.approx(100.45)


@pytest.mark.case(
    id="R4-UNIT-006",
    description="Validar regras de payload de nota antes da gravação.",
    steps="Enviar payload completo, payload sem estabelecimento e payload com tipo inválido.",
    input_data='{"data":"10/04/2026","valor":"10,50","estabelecimento":"Cliente","tipo":"Entrada"}',
    expected_output="Payload válido retorna data ISO e float; payloads inválidos retornam mensagem de erro.",
    success_criteria="A validação central impede dados incompletos ou tipos fora do domínio.",
)
def test_unit_validar_dados_nota_normaliza_e_rejeita_payloads_invalidos():
    erro, data_db, valor = validar_dados_nota(
        {
            "data": "10/04/2026",
            "valor": "10,50",
            "estabelecimento": "Cliente Unitário",
            "tipo": "Entrada",
        }
    )
    assert erro is None
    assert data_db == "2026-04-10"
    assert valor == pytest.approx(10.50)

    erro, _, _ = validar_dados_nota(
        {"data": "10/04/2026", "valor": "10,50", "estabelecimento": "", "tipo": "Entrada"}
    )
    assert erro == "Preencha o estabelecimento"

    erro, _, _ = validar_dados_nota(
        {"data": "10/04/2026", "valor": "10,50", "estabelecimento": "Cliente", "tipo": "Credito"}
    )
    assert erro == "Tipo deve ser Entrada ou Saída"


@pytest.mark.case(
    id="R4-UNIT-007",
    description="Validar autorização administrativa por header, query string e corpo JSON.",
    steps="Abrir contextos Flask de requisição com cada forma de envio do nível.",
    input_data='Header X-User-Level; query nivel; JSON {"nivel":"Administrador"}',
    expected_output="True quando Administrador; False para Gerente/Operador/ausente",
    success_criteria="A função reconhece administrador e não concede privilégio a outros níveis.",
)
def test_unit_nivel_admin_reconhece_origens_validas(flask_app):
    with flask_app.test_request_context(headers={"X-User-Level": "Administrador"}):
        assert nivel_eh_admin() is True

    with flask_app.test_request_context("/?nivel=Administrador"):
        assert nivel_eh_admin() is True

    with flask_app.test_request_context(json={"nivel": "Administrador"}):
        assert nivel_eh_admin({"nivel": "Administrador"}) is True

    with flask_app.test_request_context(headers={"X-User-Level": "Gerente"}):
        assert nivel_eh_admin() is False


@pytest.mark.case(
    id="R4-UNIT-008",
    description="Validar serialização de uma linha SQLite para JSON da API.",
    steps="Construir uma linha sqlite3.Row e chamar serializar_nota.",
    input_data="Registro com data 2026-04-10, valor 99.99 e tipo Entrada",
    expected_output="Dicionário com data 10/04/2026 e campos de nota preservados",
    success_criteria="A serialização entrega o contrato JSON usado pelos endpoints.",
)
def test_unit_serializar_nota_converte_row_para_contrato_json(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute("SELECT * FROM notas WHERE estabelecimento = ?", ("Cliente Escola Alfa",)).fetchone()
    finally:
        conn.close()

    nota = serializar_nota(row)
    assert nota == {
        "id": 1,
        "data": "10/04/2026",
        "valor": 1200.0,
        "estabelecimento": "Cliente Escola Alfa",
        "categoria": "Venda",
        "tipo": "Entrada",
        "descricao": "Material escolar",
        "arquivo_xml": "",
    }


@pytest.mark.case(
    id="R4-UNIT-009",
    description="Validar datas extremas: ano bissexto válido, ano não bissexto inválido e espaços ao redor.",
    steps="Chamar data_para_db e validar_data_emissao com datas bissextas e texto com espaços.",
    input_data='"29/02/2024"; "29/02/2025"; " 10/04/2026 "',
    expected_output='"2024-02-29"; False para 2025; True para data com espaços',
    success_criteria="A validação diferencia ano bissexto real e tolera espaços acidentais.",
)
def test_unit_datas_extremas_bissexto_e_espacos():
    assert data_para_db("29/02/2024") == "2024-02-29"
    assert validar_data_emissao("29/02/2024") is True
    assert data_para_db("29/02/2025") is None
    assert validar_data_emissao("29/02/2025") is False
    assert validar_data_emissao(" 10/04/2026 ") is True


@pytest.mark.case(
    id="R4-UNIT-010",
    description="Validar rejeição de valores numéricos especiais e formatos ambíguos.",
    steps="Chamar validar_valor_nota com NaN, infinito, string vazia, moeda formatada e separador duplicado.",
    input_data='"nan"; "inf"; ""; "R$ 10,00"; "1.234,56"',
    expected_output="False para todas as entradas",
    success_criteria="O validador não aceita valores não finitos nem formatos monetários ambíguos.",
)
def test_unit_valores_extremos_rejeita_nan_infinito_e_formatos_ambiguos():
    for valor in ["nan", "NaN", "inf", "-inf", "", "   ", "R$ 10,00", "1.234,56"]:
        assert validar_valor_nota(valor) is False


@pytest.mark.case(
    id="R4-UNIT-011",
    description="Validar payloads extremos com campos ausentes, None e estabelecimento em branco.",
    steps="Chamar validar_dados_nota com dicionários incompletos ou com espaços em campos obrigatórios.",
    input_data="{}; estabelecimento='   '; valor=None; data=None",
    expected_output="Mensagens de erro controladas sem exceções Python",
    success_criteria="A validação falha de forma previsível mesmo com payloads malformados.",
)
def test_unit_validar_dados_nota_payloads_malformados_nao_estouram_excecao():
    erro, _, _ = validar_dados_nota({})
    assert erro == "Data inválida ou no futuro"

    erro, _, _ = validar_dados_nota(
        {"data": "10/04/2026", "valor": "15", "estabelecimento": "   ", "tipo": "Entrada"}
    )
    assert erro == "Preencha o estabelecimento"

    erro, _, _ = validar_dados_nota(
        {"data": "10/04/2026", "valor": None, "estabelecimento": "Cliente", "tipo": "Entrada"}
    )
    assert erro == "O valor deve ser positivo"

    erro, _, _ = validar_dados_nota(
        {"data": None, "valor": "15", "estabelecimento": "Cliente", "tipo": "Entrada"}
    )
    assert erro == "Data inválida ou no futuro"


@pytest.mark.case(
    id="R4-UNIT-012",
    description="Validar cálculo financeiro em volume alto e com saldo negativo.",
    steps="Gerar 1000 entradas pequenas e 1000 saídas maiores e calcular o resumo.",
    input_data="1000 entradas de 0.01; 1000 saídas de 0.02",
    expected_output="entradas=10.00; saidas=20.00; saldo=-10.00",
    success_criteria="O resumo continua correto em volume alto e saldo negativo.",
)
def test_unit_resumo_financeiro_volume_alto_saldo_negativo():
    registros = []
    for i in range(1000):
        registros.append((i, "2026-04-01", 0.01, "Cliente", "Venda", "Entrada", "", ""))
        registros.append((i + 1000, "2026-04-01", 0.02, "Fornecedor", "Despesa", "Saída", "", ""))

    resumo = calcular_resumo_financeiro(registros)
    assert resumo["entradas"] == pytest.approx(10.00)
    assert resumo["saidas"] == pytest.approx(20.00)
    assert resumo["saldo"] == pytest.approx(-10.00)


# ============================================================
# TESTES DE API
# ============================================================


@pytest.mark.case(
    id="R4-API-001",
    description="Validar disponibilidade do serviço Flask.",
    steps="Executar GET /api/health usando Flask test_client.",
    input_data="GET /api/health",
    expected_output='HTTP 200 com {"status":"ok","servico":"Controle Fiscal TechStore"}',
    success_criteria="O endpoint responde 200 e identifica o serviço correto.",
)
def test_api_healthcheck_retorna_status_ok(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.get_json() == {
        "status": "ok",
        "servico": "Controle Fiscal TechStore",
    }


@pytest.mark.case(
    id="R4-API-002",
    description="Validar autenticação dos três perfis padrão.",
    steps="Executar POST /api/login para admin, gerente e caixa.",
    input_data="admin/admin; gerente/123; caixa/123",
    expected_output="HTTP 200 com níveis Administrador, Gerente e Operador",
    success_criteria="Cada usuário retorna o nível de acesso esperado.",
)
def test_api_login_autentica_perfis_padrao(client):
    casos = [
        ("admin", "admin", "Administrador"),
        ("gerente", "123", "Gerente"),
        ("caixa", "123", "Operador"),
    ]
    for username, password, nivel in casos:
        response = client.post("/api/login", json={"username": username, "password": password})
        assert response.status_code == 200
        payload = response.get_json()
        assert payload["username"] == username
        assert payload["nivel"] == nivel


@pytest.mark.case(
    id="R4-API-003",
    description="Validar rejeição de credenciais incorretas.",
    steps="Executar POST /api/login com senha inválida.",
    input_data='{"username":"admin","password":"errada"}',
    expected_output='HTTP 401 com {"erro":"Login inválido"}',
    success_criteria="Credenciais inválidas não geram sessão nem dados de usuário.",
)
def test_api_login_rejeita_senha_incorreta(client):
    response = client.post("/api/login", json={"username": "admin", "password": "errada"})
    assert response.status_code == 401
    assert response.get_json() == {"erro": "Login inválido"}


@pytest.mark.case(
    id="R4-API-004",
    description="Validar listagem inicial determinística de notas.",
    steps="Executar GET /api/notas no banco isolado da rodada 4.",
    input_data="GET /api/notas",
    expected_output="Quatro notas ordenadas por data decrescente",
    success_criteria="A API retorna todos os registros seedados e o contrato JSON completo.",
)
def test_api_listar_notas_retorna_seed_ordenado(client):
    response = client.get("/api/notas")
    notas = response.get_json()
    assert response.status_code == 200
    assert len(notas) == 4
    assert [nota["data"] for nota in notas] == [
        "13/04/2026",
        "12/04/2026",
        "11/04/2026",
        "10/04/2026",
    ]
    assert set(notas[0]) == {
        "id",
        "data",
        "valor",
        "estabelecimento",
        "categoria",
        "tipo",
        "descricao",
        "arquivo_xml",
    }


@pytest.mark.case(
    id="R4-API-005",
    description="Validar filtros por texto e por intervalo de datas.",
    steps="Executar GET /api/notas com busca e depois com inicio/fim.",
    input_data='busca="Venda B2B"; inicio="11/04/2026"; fim="12/04/2026"',
    expected_output="Filtro textual retorna Venda B2B; período retorna dias 11 e 12/04/2026",
    success_criteria="Os filtros restringem corretamente os registros retornados.",
)
def test_api_filtros_por_texto_e_periodo(client):
    por_texto = client.get("/api/notas", query_string={"busca": "Venda B2B"})
    assert por_texto.status_code == 200
    assert [nota["estabelecimento"] for nota in por_texto.get_json()] == ["Cliente Escritório Beta"]

    por_periodo = client.get(
        "/api/notas",
        query_string={"inicio": "11/04/2026", "fim": "12/04/2026"},
    )
    assert por_periodo.status_code == 200
    assert [nota["data"] for nota in por_periodo.get_json()] == ["12/04/2026", "11/04/2026"]


@pytest.mark.case(
    id="R4-API-006",
    description="Validar criação de nota de entrada e impacto no resumo.",
    steps="Executar POST /api/notas com payload válido e consultar /api/resumo.",
    input_data='{"data":"15/04/2026","valor":"250,50","tipo":"Entrada"}',
    expected_output="HTTP 201 com id; entradas aumentam para 1901.25 e saldo para 1421.00",
    success_criteria="A nota é persistida com valor decimal correto e refletida no resumo financeiro.",
)
def test_api_criar_nota_valida_atualiza_resumo(client, case_data):
    response = client.post("/api/notas", json=case_data["entrada_valida"])
    assert response.status_code == 201
    assert isinstance(response.get_json()["id"], int)

    resumo = client.get("/api/resumo").get_json()
    assert resumo["entradas"] == pytest.approx(1901.25)
    assert resumo["saidas"] == pytest.approx(480.25)
    assert resumo["saldo"] == pytest.approx(1421.00)


@pytest.mark.case(
    id="R4-API-007",
    description="Validar rejeição de payloads inválidos no cadastro de nota.",
    steps="Enviar notas com data futura, valor zero, estabelecimento vazio e tipo inválido.",
    input_data="4 payloads inválidos para POST /api/notas",
    expected_output="HTTP 400 com mensagem de erro específica para cada payload",
    success_criteria="Nenhum payload inválido é aceito pelo endpoint de cadastro.",
)
def test_api_criar_nota_rejeita_payloads_invalidos(client):
    amanha = (datetime.now() + timedelta(days=1)).strftime("%d/%m/%Y")
    casos = [
        (
            {"data": amanha, "valor": "10", "estabelecimento": "Cliente", "tipo": "Entrada"},
            "Data inválida ou no futuro",
        ),
        (
            {"data": "15/04/2026", "valor": "0", "estabelecimento": "Cliente", "tipo": "Entrada"},
            "O valor deve ser positivo",
        ),
        (
            {"data": "15/04/2026", "valor": "10", "estabelecimento": "", "tipo": "Entrada"},
            "Preencha o estabelecimento",
        ),
        (
            {"data": "15/04/2026", "valor": "10", "estabelecimento": "Cliente", "tipo": "Credito"},
            "Tipo deve ser Entrada ou Saída",
        ),
    ]
    for payload, erro in casos:
        response = client.post("/api/notas", json=payload)
        assert response.status_code == 400
        assert response.get_json() == {"erro": erro}


@pytest.mark.case(
    id="R4-API-008",
    description="Validar edição de nota protegida por permissão administrativa.",
    steps="Tentar PUT como Gerente e depois repetir como Administrador.",
    input_data="PUT /api/notas/1 com X-User-Level Gerente e Administrador",
    expected_output="Gerente recebe 403; Administrador recebe 200 e nota atualizada",
    success_criteria="Apenas administrador consegue alterar operações existentes.",
)
def test_api_editar_nota_exige_admin_e_persiste_alteracao(client):
    payload = {
        "data": "16/04/2026",
        "valor": "333,33",
        "estabelecimento": "Cliente Editado",
        "categoria": "Venda Ajustada",
        "tipo": "Entrada",
        "descricao": "Alterado pela rodada 4",
        "arquivo_xml": "nota.xml",
    }
    negado = client.put("/api/notas/1", json=payload, headers={"X-User-Level": "Gerente"})
    assert negado.status_code == 403

    autorizado = client.put("/api/notas/1", json=payload, headers={"X-User-Level": "Administrador"})
    assert autorizado.status_code == 200
    assert autorizado.get_json() == {"status": "atualizada", "id": 1}

    busca = client.get("/api/notas", query_string={"busca": "Editado"}).get_json()
    assert len(busca) == 1
    assert busca[0]["valor"] == pytest.approx(333.33)
    assert busca[0]["descricao"] == "Alterado pela rodada 4"


@pytest.mark.case(
    id="R4-API-009",
    description="Validar exclusão de nota protegida por permissão administrativa.",
    steps="Tentar DELETE como Operador e depois repetir como Administrador.",
    input_data="DELETE /api/notas/2 com nivel Operador e Administrador",
    expected_output="Operador recebe 403; Administrador recebe 200; nota deixa de aparecer",
    success_criteria="A exclusão respeita permissão e remove o registro do banco.",
)
def test_api_excluir_nota_exige_admin_e_remove_registro(client):
    negado = client.delete("/api/notas/2", json={"nivel": "Operador"})
    assert negado.status_code == 403

    autorizado = client.delete("/api/notas/2", json={"nivel": "Administrador"})
    assert autorizado.status_code == 200
    assert autorizado.get_json() == {"status": "excluida", "id": 2}

    busca = client.get("/api/notas", query_string={"busca": "Escritório Beta"}).get_json()
    assert busca == []


@pytest.mark.case(
    id="R4-API-010",
    description="Validar tratamento de recurso inexistente em edição e exclusão.",
    steps="Executar PUT e DELETE para nota id 999 como Administrador.",
    input_data="PUT /api/notas/999; DELETE /api/notas/999",
    expected_output='HTTP 404 com {"erro":"Operação não encontrada"}',
    success_criteria="Operações sobre IDs inexistentes retornam erro controlado.",
)
def test_api_editar_e_excluir_id_inexistente_retorna_404(client):
    payload = {
        "data": "16/04/2026",
        "valor": "100",
        "estabelecimento": "Cliente",
        "categoria": "Venda",
        "tipo": "Entrada",
    }
    editar = client.put("/api/notas/999", json=payload, headers={"X-User-Level": "Administrador"})
    excluir = client.delete("/api/notas/999", json={"nivel": "Administrador"})

    assert editar.status_code == 404
    assert editar.get_json() == {"erro": "Operação não encontrada"}
    assert excluir.status_code == 404
    assert excluir.get_json() == {"erro": "Operação não encontrada"}


@pytest.mark.case(
    id="R4-API-011",
    description="Validar busca com texto agressivo semelhante a SQL injection.",
    steps="Executar GET /api/notas com termo contendo aspas, operador OR e comentario SQL.",
    input_data='busca="\' OR 1=1 --"',
    expected_output="HTTP 200 com lista vazia e banco ainda íntegro",
    success_criteria="O endpoint usa parâmetros SQL e não transforma o termo em comando executável.",
)
def test_api_busca_com_padrao_sql_injection_nao_vaza_todos_os_registros(client):
    response = client.get("/api/notas", query_string={"busca": "' OR 1=1 --"})
    assert response.status_code == 200
    assert response.get_json() == []

    controle = client.get("/api/notas")
    assert controle.status_code == 200
    assert len(controle.get_json()) == 4


@pytest.mark.case(
    id="R4-API-012",
    description="Validar cadastro com unicode, símbolos e valor muito alto.",
    steps="Executar POST /api/notas com acentos, emoji, XML com caminho simbólico e valor milionário.",
    input_data='estabelecimento="São José & Filhos - Café"; valor="999999999,99"',
    expected_output="HTTP 201; listagem preserva unicode; resumo incorpora valor 999999999.99",
    success_criteria="A API persiste caracteres não ASCII e calcula total alto sem truncar centavos.",
)
def test_api_cria_nota_unicode_simbolos_e_valor_muito_alto(client):
    payload = {
        "data": "17/04/2026",
        "valor": "999999999,99",
        "estabelecimento": "São José & Filhos - Café",
        "categoria": "Venda Especial / Ünicode",
        "tipo": "Entrada",
        "descricao": "Pedido crítico com acentuação e símbolo #42",
        "arquivo_xml": "../xmls/nota-especial.xml",
    }
    cadastro = client.post("/api/notas", json=payload)
    assert cadastro.status_code == 201

    busca = client.get("/api/notas", query_string={"busca": "São José"}).get_json()
    assert len(busca) == 1
    assert busca[0]["estabelecimento"] == "São José & Filhos - Café"
    assert busca[0]["valor"] == pytest.approx(999999999.99)

    resumo = client.get("/api/resumo").get_json()
    assert resumo["entradas"] == pytest.approx(1000001650.74)
    assert resumo["saldo"] == pytest.approx(1000001170.49)


@pytest.mark.case(
    id="R4-API-013",
    description="Validar requisição sem JSON ou com JSON vazio.",
    steps="Enviar POST /api/notas sem corpo JSON e depois com objeto vazio.",
    input_data="body text/plain vazio; json={}",
    expected_output='HTTP 400 com erro "Data inválida ou no futuro"',
    success_criteria="O endpoint responde erro controlado e não lança exceção 500.",
)
def test_api_cadastro_sem_json_ou_json_vazio_retorna_400_controlado(client):
    sem_json = client.post("/api/notas", data="nao-json", content_type="text/plain")
    vazio = client.post("/api/notas", json={})

    assert sem_json.status_code == 400
    assert sem_json.get_json() == {"erro": "Data inválida ou no futuro"}
    assert vazio.status_code == 400
    assert vazio.get_json() == {"erro": "Data inválida ou no futuro"}


@pytest.mark.case(
    id="R4-API-014",
    description="Validar rejeição de estabelecimento composto apenas por espaços.",
    steps="Executar POST /api/notas com estabelecimento='   '.",
    input_data='{"data":"18/04/2026","valor":"10","estabelecimento":"   ","tipo":"Entrada"}',
    expected_output='HTTP 400 com {"erro":"Preencha o estabelecimento"}',
    success_criteria="Campos obrigatórios com apenas espaços não podem gerar registro financeiro.",
)
def test_api_rejeita_estabelecimento_apenas_com_espacos(client):
    response = client.post(
        "/api/notas",
        json={"data": "18/04/2026", "valor": "10", "estabelecimento": "   ", "tipo": "Entrada"},
    )
    assert response.status_code == 400
    assert response.get_json() == {"erro": "Preencha o estabelecimento"}


@pytest.mark.case(
    id="R4-API-015",
    description="Validar rejeição de NaN e infinito em valor financeiro pela API.",
    steps="Executar POST /api/notas com valor='nan' e valor='inf'.",
    input_data='valor="nan"; valor="inf"',
    expected_output='HTTP 400 com {"erro":"O valor deve ser positivo"}',
    success_criteria="Valores não finitos não podem ser persistidos nem entrar no resumo financeiro.",
)
def test_api_rejeita_nan_e_infinito_em_valor_financeiro(client):
    for valor in ["nan", "inf"]:
        response = client.post(
            "/api/notas",
            json={
                "data": "18/04/2026",
                "valor": valor,
                "estabelecimento": "Cliente Valor Especial",
                "categoria": "Venda",
                "tipo": "Entrada",
            },
        )
        assert response.status_code == 400
        assert response.get_json() == {"erro": "O valor deve ser positivo"}


@pytest.mark.case(
    id="R4-API-016",
    description="Validar exclusão repetida da mesma nota.",
    steps="Excluir uma nota como Administrador e repetir a mesma exclusão.",
    input_data="DELETE /api/notas/3 duas vezes",
    expected_output="Primeira chamada HTTP 200; segunda chamada HTTP 404",
    success_criteria="O endpoint é consistente após remover o registro e não finge excluir duas vezes.",
)
def test_api_exclusao_repetida_retorna_404_na_segunda_tentativa(client):
    primeira = client.delete("/api/notas/3", json={"nivel": "Administrador"})
    segunda = client.delete("/api/notas/3", json={"nivel": "Administrador"})

    assert primeira.status_code == 200
    assert primeira.get_json() == {"status": "excluida", "id": 3}
    assert segunda.status_code == 404
    assert segunda.get_json() == {"erro": "Operação não encontrada"}


# ============================================================
# TESTES E2E
# ============================================================


@pytest.mark.case(
    id="R4-E2E-001",
    description="Validar fluxo do usuário: login, cadastro, busca e consulta de resumo em navegador.",
    steps="Abrir harness web da rodada 4, preencher credenciais, salvar uma entrada, buscar a nota e consultar resumo.",
    input_data="admin/admin; nota Entrada de R$ 250,50 para Cliente Rodada 4",
    expected_output="Login exibe Administrador; cadastro retorna salvo:id; busca lista a nota; resumo inclui saldo atualizado.",
    success_criteria="O fluxo completo funciona via HTTP real usando Playwright com Chromium headless.",
)
def test_e2e_playwright_login_cadastro_busca_e_resumo(live_server, case_data):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(live_server, wait_until="networkidle")

            page.get_by_label("Usuário").fill("admin")
            page.get_by_label("Senha").fill("admin")
            page.locator("#login").click()
            expect(page.locator("#login-result")).to_have_text("Administrador")

            nota = case_data["entrada_valida"]
            page.get_by_label("Data").fill(nota["data"])
            page.get_by_label("Valor").fill(nota["valor"])
            page.get_by_label("Estabelecimento").fill(nota["estabelecimento"])
            page.get_by_label("Categoria").fill(nota["categoria"])
            page.get_by_label("Tipo").select_option(nota["tipo"])
            page.get_by_label("Descrição").fill(nota["descricao"])
            page.locator("#salvar").click()
            expect(page.locator("#save-result")).to_contain_text("salvo:")

            page.get_by_label("Busca").fill("Cliente Rodada 4")
            page.locator("#buscar").click()
            expect(page.locator("#notas li")).to_have_count(1)
            expect(page.locator("#notas li").first).to_contain_text("Cliente Rodada 4|Venda|250.5")

            page.locator("#resumo").click()
            expect(page.locator("#summary")).to_contain_text('"saldo"')
            resumo = json.loads(page.locator("#summary").text_content())
            assert resumo["entradas"] == pytest.approx(1901.25)
            assert resumo["saidas"] == pytest.approx(480.25)
            assert resumo["saldo"] == pytest.approx(1421.00)
        finally:
            browser.close()


@pytest.mark.case(
    id="R4-E2E-002",
    description="Validar mensagem de erro ao usuário ao tentar cadastrar nota inválida.",
    steps="Abrir o harness, preencher uma nota com data futura e clicar em salvar.",
    input_data="data de amanhã; valor 100; tipo Entrada",
    expected_output='Mensagem "Data inválida ou no futuro" exibida no output de cadastro',
    success_criteria="O navegador recebe e mostra a validação da API sem gravar a nota.",
)
def test_e2e_playwright_cadastro_invalido_mostra_erro(live_server):
    amanha = (datetime.now() + timedelta(days=1)).strftime("%d/%m/%Y")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(live_server, wait_until="networkidle")
            page.get_by_label("Data").fill(amanha)
            page.get_by_label("Valor").fill("100")
            page.get_by_label("Estabelecimento").fill("Cliente Futuro")
            page.get_by_label("Categoria").fill("Venda")
            page.get_by_label("Tipo").select_option("Entrada")
            page.get_by_label("Descrição").fill("Tentativa inválida")
            page.locator("#salvar").click()

            expect(page.locator("#save-result")).to_have_text("Data inválida ou no futuro")

            page.get_by_label("Busca").fill("Cliente Futuro")
            page.locator("#buscar").click()
            expect(page.locator("#notas li")).to_have_count(0)
        finally:
            browser.close()


@pytest.mark.case(
    id="R4-E2E-003",
    description="Validar navegação de consulta sem cadastro novo, simulando busca operacional do usuário.",
    steps="Abrir harness, buscar por fornecedor existente e conferir a linha retornada.",
    input_data='busca="Fornecedor Papel Sul"',
    expected_output="Uma linha contendo Compra de Estoque e valor 300.25",
    success_criteria="A consulta usada na tela retorna exatamente a operação filtrada.",
)
def test_e2e_playwright_busca_operacional_existente(live_server):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(live_server, wait_until="networkidle")
            page.get_by_label("Busca").fill("Fornecedor Papel Sul")
            page.locator("#buscar").click()

            expect(page.locator("#notas li")).to_have_count(1)
            expect(page.locator("#notas li").first).to_contain_text("Fornecedor Papel Sul")
            expect(page.locator("#notas li").first).to_contain_text("Compra de Estoque")
            expect(page.locator("#notas li").first).to_contain_text("300.25")
        finally:
            browser.close()


@pytest.mark.case(
    id="R4-E2E-004",
    description="Validar fluxo extremo no navegador com unicode, valor alto e busca por acento.",
    steps="Abrir harness, cadastrar uma nota com texto acentuado e valor alto, buscar por parte acentuada e consultar resumo.",
    input_data='estabelecimento="São José & Filhos - Café"; valor="999999999,99"',
    expected_output="Cadastro salvo, busca retorna uma linha e resumo contém entrada acima de 1 bilhão.",
    success_criteria="O fluxo E2E preserva unicode e calcula valor alto via navegador + Flask real.",
)
def test_e2e_playwright_unicode_e_valor_muito_alto(live_server):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(live_server, wait_until="networkidle")
            page.get_by_label("Data").fill("17/04/2026")
            page.get_by_label("Valor").fill("999999999,99")
            page.get_by_label("Estabelecimento").fill("São José & Filhos - Café")
            page.get_by_label("Categoria").fill("Venda Especial / Ünicode")
            page.get_by_label("Tipo").select_option("Entrada")
            page.get_by_label("Descrição").fill("Pedido crítico #42")
            page.locator("#salvar").click()
            expect(page.locator("#save-result")).to_contain_text("salvo:")

            page.get_by_label("Busca").fill("São José")
            page.locator("#buscar").click()
            expect(page.locator("#notas li")).to_have_count(1)
            expect(page.locator("#notas li").first).to_contain_text("São José & Filhos - Café")
            expect(page.locator("#notas li").first).to_contain_text("999999999.99")

            page.locator("#resumo").click()
            expect(page.locator("#summary")).to_contain_text('"saldo"')
            resumo = json.loads(page.locator("#summary").text_content())
            assert resumo["entradas"] == pytest.approx(1000001650.74)
            assert resumo["saldo"] == pytest.approx(1000001170.49)
        finally:
            browser.close()


@pytest.mark.case(
    id="R4-E2E-005",
    description="Validar busca agressiva no navegador sem vazar registros.",
    steps="Abrir harness, preencher busca com texto parecido com SQL injection e conferir lista vazia.",
    input_data='busca="\' OR 1=1 --"',
    expected_output="Nenhuma linha renderizada na lista de notas.",
    success_criteria="O fluxo navegador/API não transforma texto de busca em comando SQL.",
)
def test_e2e_playwright_busca_agressiva_nao_vaza_registros(live_server):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(live_server, wait_until="networkidle")
            page.get_by_label("Busca").fill("' OR 1=1 --")
            page.locator("#buscar").click()
            expect(page.locator("#notas li")).to_have_count(0)
        finally:
            browser.close()


@pytest.mark.case(
    id="R4-E2E-006",
    description="Validar defeito conhecido no navegador: estabelecimento só com espaços é aceito indevidamente.",
    steps="Abrir harness, cadastrar nota com estabelecimento contendo apenas espaços e observar resposta.",
    input_data='estabelecimento="   "; valor="10"; data="18/04/2026"',
    expected_output='Mensagem "Preencha o estabelecimento" no output de cadastro',
    success_criteria="A UI/API deveria bloquear campo obrigatório visualmente vazio.",
)
def test_e2e_playwright_deveria_rejeitar_estabelecimento_apenas_espacos(live_server):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(live_server, wait_until="networkidle")
            page.get_by_label("Data").fill("18/04/2026")
            page.get_by_label("Valor").fill("10")
            page.get_by_label("Estabelecimento").fill("   ")
            page.get_by_label("Categoria").fill("Venda")
            page.get_by_label("Tipo").select_option("Entrada")
            page.get_by_label("Descrição").fill("Campo obrigatorio vazio")
            page.locator("#salvar").click()
            expect(page.locator("#save-result")).to_have_text("Preencha o estabelecimento")
        finally:
            browser.close()
