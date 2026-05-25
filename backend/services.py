from datetime import datetime


def validar_data_emissao(data_str):
    try:
        dt = datetime.strptime(data_str, "%d/%m/%Y")
        if dt > datetime.now():
            return False
        return True
    except ValueError:
        return False


def validar_valor_nota(valor_str):
    try:
        v = float(valor_str.replace(",", "."))
        if v <= 0:
            return False
        return True
    except ValueError:
        return False


def calcular_resumo_financeiro(registros):
    res = {"entradas": 0.0, "saidas": 0.0, "saldo": 0.0}
    for r in registros:
        valor = r[2]
        if r[5] == "Entrada":
            res["entradas"] += valor
            res["saldo"] += valor
        else:
            res["saidas"] += valor
            res["saldo"] -= valor
    return res


def data_para_db(data_str):
    try:
        return datetime.strptime(data_str, "%d/%m/%Y").strftime("%Y-%m-%d")
    except ValueError:
        return None


def data_para_ui(data_str):
    try:
        return datetime.strptime(data_str, "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return data_str
