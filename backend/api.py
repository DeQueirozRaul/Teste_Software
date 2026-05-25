import sqlite3
from pathlib import Path

from flask import Flask, jsonify, request

from backend.database import init_db
from backend.services import data_para_db, data_para_ui
from backend.services import validar_data_emissao, validar_valor_nota


def conectar(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def garantir_banco(db_path):
    db_path = Path(db_path)
    if db_path.name != "notas_fiscais.db":
        return

    cwd_original = Path.cwd()
    try:
        if db_path.parent != Path("."):
            import os

            os.chdir(db_path.parent)
        init_db()
    finally:
        import os

        os.chdir(cwd_original)


def criar_app(db_path="notas_fiscais.db"):
    app = Flask(__name__)
    app.config["DB_PATH"] = str(db_path)
    garantir_banco(app.config["DB_PATH"])

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok", "servico": "Controle Fiscal TechStore"})

    @app.post("/api/login")
    def login():
        dados = request.get_json(silent=True) or {}
        conn = conectar(app.config["DB_PATH"])
        try:
            usuario = conn.execute(
                """
                SELECT id, username, nivel
                FROM usuarios
                WHERE username = ? AND password = ?
                """,
                (dados.get("username"), dados.get("password")),
            ).fetchone()
        finally:
            conn.close()

        if usuario is None:
            return jsonify({"erro": "Login inválido"}), 401

        return jsonify(
            {
                "id": usuario["id"],
                "username": usuario["username"],
                "nivel": usuario["nivel"],
            }
        )

    @app.get("/api/notas")
    def listar_notas():
        query = "SELECT * FROM notas WHERE 1=1"
        params = []

        busca = request.args.get("busca")
        if busca:
            query += " AND (estabelecimento LIKE ? OR categoria LIKE ? OR descricao LIKE ?)"
            params.extend([f"%{busca}%", f"%{busca}%", f"%{busca}%"])

        inicio = request.args.get("inicio")
        if inicio:
            dt_inicio = data_para_db(inicio)
            if dt_inicio:
                query += " AND data >= ?"
                params.append(dt_inicio)

        fim = request.args.get("fim")
        if fim:
            dt_fim = data_para_db(fim)
            if dt_fim:
                query += " AND data <= ?"
                params.append(dt_fim)

        conn = conectar(app.config["DB_PATH"])
        try:
            registros = conn.execute(query + " ORDER BY data DESC", params).fetchall()
        finally:
            conn.close()

        return jsonify([serializar_nota(r) for r in registros])

    @app.post("/api/notas")
    def criar_nota():
        dados = request.get_json(silent=True) or {}

        if not validar_data_emissao(dados.get("data", "")):
            return jsonify({"erro": "Data inválida ou no futuro"}), 400

        if not validar_valor_nota(str(dados.get("valor", ""))):
            return jsonify({"erro": "O valor deve ser positivo"}), 400

        if not dados.get("estabelecimento"):
            return jsonify({"erro": "Preencha o estabelecimento"}), 400

        if dados.get("tipo", "Entrada") not in ("Entrada", "Saída"):
            return jsonify({"erro": "Tipo deve ser Entrada ou Saída"}), 400

        data_db = data_para_db(dados["data"])
        valor = float(str(dados["valor"]).replace(",", "."))
        conn = conectar(app.config["DB_PATH"])
        try:
            cursor = conn.execute(
                """
                INSERT INTO notas
                    (data, valor, estabelecimento, categoria, tipo, descricao, arquivo_xml)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data_db,
                    valor,
                    dados["estabelecimento"],
                    dados.get("categoria", ""),
                    dados.get("tipo", "Entrada"),
                    dados.get("descricao", ""),
                    dados.get("arquivo_xml", ""),
                ),
            )
            conn.commit()
            nota_id = cursor.lastrowid
        finally:
            conn.close()

        return jsonify({"id": nota_id}), 201

    @app.get("/api/resumo")
    def resumo():
        conn = conectar(app.config["DB_PATH"])
        try:
            resumo = conn.execute(
                """
                SELECT
                    COALESCE(SUM(CASE WHEN tipo = 'Entrada' THEN valor ELSE 0 END), 0) AS entradas,
                    COALESCE(SUM(CASE WHEN tipo = 'Saída' THEN valor ELSE 0 END), 0) AS saidas
                FROM notas
                """
            ).fetchone()
        finally:
            conn.close()

        entradas = resumo["entradas"]
        saidas = resumo["saidas"]
        return jsonify(
            {
                "entradas": entradas,
                "saidas": saidas,
                "saldo": entradas - saidas,
            }
        )

    return app


def serializar_nota(registro):
    return {
        "id": registro["id"],
        "data": data_para_ui(registro["data"]),
        "valor": registro["valor"],
        "estabelecimento": registro["estabelecimento"],
        "categoria": registro["categoria"],
        "tipo": registro["tipo"],
        "descricao": registro["descricao"],
        "arquivo_xml": registro["arquivo_xml"],
    }


if __name__ == "__main__":
    criar_app().run(host="127.0.0.1", port=5000, debug=True)
