import json
import sqlite3
import sys
import threading
import time
from pathlib import Path
from urllib import request

import pytest
from werkzeug.serving import make_server

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.api import criar_app


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "case(id, description, steps, input_data, expected_output, success_criteria): "
        "documenta um caso de teste da rodada 4",
    )


def criar_schema_teste(db_path):
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(
            """
            CREATE TABLE usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT,
                nivel TEXT
            );

            CREATE TABLE notas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT,
                valor REAL,
                estabelecimento TEXT,
                categoria TEXT,
                tipo TEXT,
                descricao TEXT,
                arquivo_xml TEXT
            );
            """
        )
        conn.executemany(
            "INSERT INTO usuarios (username, password, nivel) VALUES (?, ?, ?)",
            [
                ("admin", "admin", "Administrador"),
                ("gerente", "123", "Gerente"),
                ("caixa", "123", "Operador"),
            ],
        )
        conn.executemany(
            """
            INSERT INTO notas
                (data, valor, estabelecimento, categoria, tipo, descricao, arquivo_xml)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                ("2026-04-10", 1200.00, "Cliente Escola Alfa", "Venda", "Entrada", "Material escolar", ""),
                ("2026-04-11", 450.75, "Cliente Escritório Beta", "Venda B2B", "Entrada", "Papelaria corporativa", ""),
                ("2026-04-12", 300.25, "Fornecedor Papel Sul", "Compra de Estoque", "Saída", "Reposição A4", ""),
                ("2026-04-13", 180.00, "Enel", "Despesa Fixa", "Saída", "Conta de energia", ""),
            ],
        )
        conn.commit()
    finally:
        conn.close()


@pytest.fixture()
def db_path(tmp_path):
    path = tmp_path / "rodada4.sqlite"
    criar_schema_teste(path)
    return path


@pytest.fixture()
def flask_app(db_path):
    app = criar_app(db_path)
    app.config.update(TESTING=True)
    return app


@pytest.fixture()
def client(flask_app):
    return flask_app.test_client()


@pytest.fixture()
def live_server(flask_app):
    html_page = """
    <!doctype html>
    <html lang="pt-BR">
      <head><meta charset="utf-8"><title>Harness E2E Rodada 4</title></head>
      <body>
        <input id="username" aria-label="Usuário">
        <input id="password" aria-label="Senha">
        <button id="login">Entrar</button>
        <output id="login-result"></output>

        <input id="data" aria-label="Data">
        <input id="valor" aria-label="Valor">
        <input id="estabelecimento" aria-label="Estabelecimento">
        <input id="categoria" aria-label="Categoria">
        <select id="tipo" aria-label="Tipo">
          <option>Entrada</option>
          <option>Saída</option>
        </select>
        <input id="descricao" aria-label="Descrição">
        <button id="salvar">Salvar</button>
        <output id="save-result"></output>

        <input id="busca" aria-label="Busca">
        <button id="buscar">Buscar</button>
        <ul id="notas"></ul>
        <button id="resumo">Resumo</button>
        <output id="summary"></output>

        <script>
          window.usuario = null;

          async function jsonFetch(url, options = {}) {
            const response = await fetch(url, {
              headers: {"Content-Type": "application/json", ...(options.headers || {})},
              ...options
            });
            const data = await response.json();
            return {ok: response.ok, status: response.status, data};
          }

          document.querySelector("#login").addEventListener("click", async () => {
            const result = await jsonFetch("/api/login", {
              method: "POST",
              body: JSON.stringify({
                username: document.querySelector("#username").value,
                password: document.querySelector("#password").value
              })
            });
            window.usuario = result.data;
            document.querySelector("#login-result").textContent = result.ok ? result.data.nivel : result.data.erro;
          });

          document.querySelector("#salvar").addEventListener("click", async () => {
            const result = await jsonFetch("/api/notas", {
              method: "POST",
              body: JSON.stringify({
                data: document.querySelector("#data").value,
                valor: document.querySelector("#valor").value,
                estabelecimento: document.querySelector("#estabelecimento").value,
                categoria: document.querySelector("#categoria").value,
                tipo: document.querySelector("#tipo").value,
                descricao: document.querySelector("#descricao").value
              })
            });
            document.querySelector("#save-result").textContent = result.ok ? `salvo:${result.data.id}` : result.data.erro;
          });

          document.querySelector("#buscar").addEventListener("click", async () => {
            const termo = encodeURIComponent(document.querySelector("#busca").value);
            const result = await jsonFetch(`/api/notas?busca=${termo}`);
            const list = document.querySelector("#notas");
            list.innerHTML = "";
            result.data.forEach((nota) => {
              const li = document.createElement("li");
              li.textContent = `${nota.estabelecimento}|${nota.categoria}|${nota.valor}`;
              list.appendChild(li);
            });
          });

          document.querySelector("#resumo").addEventListener("click", async () => {
            const result = await jsonFetch("/api/resumo");
            document.querySelector("#summary").textContent = JSON.stringify(result.data);
          });
        </script>
      </body>
    </html>
    """

    @flask_app.get("/")
    def rodada4_harness():
        return html_page

    server = make_server("127.0.0.1", 0, flask_app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"

    deadline = time.time() + 5
    while time.time() < deadline:
        try:
            request.urlopen(f"{base_url}/api/health", timeout=0.5).read()
            break
        except Exception:
            time.sleep(0.05)
    else:
        server.shutdown()
        raise RuntimeError("Servidor Flask de teste nao respondeu a tempo")

    try:
        yield base_url
    finally:
        server.shutdown()
        thread.join(timeout=2)


@pytest.fixture()
def case_data():
    return {
        "entrada_valida": {
            "data": "15/04/2026",
            "valor": "250,50",
            "estabelecimento": "Cliente Rodada 4",
            "categoria": "Venda",
            "tipo": "Entrada",
            "descricao": "Fluxo automatizado",
        }
    }


@pytest.fixture(autouse=True)
def registrar_caso_no_log_do_pytest(request):
    marker = request.node.get_closest_marker("case")
    if marker is None:
        yield
        return

    dados = marker.kwargs
    print(f"\n[CASO] {dados['id']}")
    print(f"[DESCRICAO] {dados['description']}")
    print(f"[PASSOS] {dados['steps']}")
    print(f"[ENTRADA] {dados['input_data']}")
    print(f"[SAIDA_ESPERADA] {dados['expected_output']}")
    print(f"[CRITERIO_SUCESSO] {dados['success_criteria']}")

    try:
        yield
    finally:
        print(f"[FIM] {dados['id']} executado pelo pytest")
