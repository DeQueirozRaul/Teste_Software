import sqlite3

def init_db():
    print("Inicializando banco de dados comercial...")
    conn = sqlite3.connect('notas_fiscais.db')
    cursor = conn.cursor()
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS notas 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, valor REAL, 
                       estabelecimento TEXT, categoria TEXT, tipo TEXT, arquivo_xml TEXT)''')
    
    cursor.execute("INSERT OR IGNORE INTO usuarios (username, password) VALUES ('admin', 'admin')")
    
    cursor.execute("SELECT COUNT(*) FROM notas")
    if cursor.fetchone()[0] == 0:
        print("Populando o banco com volume de dados fictícios...")
        notas_comercio = [
            # JANEIRO 2026
            ('2026-01-05', 850.00, 'Imobiliária Central', 'Aluguel', 'Saída', ''),
            ('2026-01-08', 150.00, 'Papelaria Tamoio', 'Despesa Operacional', 'Saída', ''),
            ('2026-01-10', 4500.00, 'Distribuidora Fuji', 'Compra de Estoque', 'Saída', ''),
            ('2026-01-12', 320.00, 'Cliente - João Silva', 'Venda', 'Entrada', ''),
            ('2026-01-15', 1800.00, 'Cliente - Empresa Alpha', 'Venda B2B', 'Entrada', ''),
            ('2026-01-18', 250.00, 'Companhia de Água', 'Despesa Fixa', 'Saída', ''),
            ('2026-01-20', 450.00, 'Companhia de Energia', 'Despesa Fixa', 'Saída', ''),
            ('2026-01-28', 850.00, 'Cliente - Marcos Paulo', 'Venda', 'Entrada', ''),
            ('2026-01-30', 2100.00, 'Cliente - Consultório Sorriso', 'Venda B2B', 'Entrada', ''),
            # FEVEREIRO 2026
            ('2026-02-02', 850.00, 'Imobiliária Central', 'Aluguel', 'Saída', ''),
            ('2026-02-05', 7000.00, 'Atacadão da Informática', 'Compra de Estoque', 'Saída', ''),
            ('2026-02-08', 450.00, 'Cliente - Ana Costa', 'Venda', 'Entrada', ''),
            ('2026-02-12', 300.00, 'Marketing Ads', 'Marketing', 'Saída', ''),
            ('2026-02-15', 3100.00, 'Cliente - Colégio Lápis', 'Venda B2B', 'Entrada', ''),
            ('2026-02-20', 430.00, 'Companhia de Energia', 'Despesa Fixa', 'Saída', ''),
            ('2026-02-26', 1500.00, 'Cliente - Roberto Alves', 'Venda', 'Entrada', ''),
            # MARÇO 2026
            ('2026-03-05', 850.00, 'Imobiliária Central', 'Aluguel', 'Saída', ''),
            ('2026-03-07', 5400.00, 'Distribuidora Fuji', 'Compra de Estoque', 'Saída', ''),
            ('2026-03-10', 950.00, 'Cliente - Carlos Mendes', 'Venda', 'Entrada', ''),
            ('2026-03-12', 400.00, 'Marketing Ads', 'Marketing', 'Saída', ''),
            ('2026-03-15', 4200.00, 'Cliente - Clínica Saúde', 'Venda B2B', 'Entrada', ''),
            ('2026-03-20', 480.00, 'Companhia de Energia', 'Despesa Fixa', 'Saída', ''),
            ('2026-03-28', 2200.00, 'Cliente - Maria Oliveira', 'Venda', 'Entrada', ''),
            ('2026-03-30', 150.00, 'Material de Limpeza', 'Despesa Operacional', 'Saída', ''),
            # ABRIL 2026
            ('2026-04-02', 850.00, 'Imobiliária Central', 'Aluguel', 'Saída', ''),
            ('2026-04-05', 8000.00, 'Atacadão da Informática', 'Compra de Estoque', 'Saída', ''),
            ('2026-04-08', 1200.00, 'Cliente - Thiago Silva', 'Venda', 'Entrada', '')
        ]
        cursor.executemany('INSERT INTO notas (data, valor, estabelecimento, categoria, tipo, arquivo_xml) VALUES (?,?,?,?,?,?)', notas_comercio)
    
    conn.commit()
    conn.close()
    print("Banco pronto e populado!")

if __name__ == "__main__":
    init_db()