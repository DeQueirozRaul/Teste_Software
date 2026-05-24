import sqlite3
import random
from datetime import date, timedelta

def init_db():
    print("Inicializando banco de dados (Controle de Acesso e Ajuste Financeiro)...")
    conn = sqlite3.connect('notas_fiscais.db')
    cursor = conn.cursor()
    
    # Nova tabela de usuários com a coluna 'nivel'
    cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, nivel TEXT)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS notas 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, valor REAL, 
                       estabelecimento TEXT, categoria TEXT, tipo TEXT, descricao TEXT, arquivo_xml TEXT)''')
    
    # Criando os 3 Níveis de Acesso
    cursor.execute("INSERT OR IGNORE INTO usuarios (username, password, nivel) VALUES ('admin', 'admin', 'Administrador')")
    cursor.execute("INSERT OR IGNORE INTO usuarios (username, password, nivel) VALUES ('gerente', '123', 'Gerente')")
    cursor.execute("INSERT OR IGNORE INTO usuarios (username, password, nivel) VALUES ('caixa', '123', 'Operador')")
    
    cursor.execute("SELECT COUNT(*) FROM notas")
    if cursor.fetchone()[0] == 0:
        print("Gerando registros com margem de lucro de 20% a 25%... Aguarde!")
        
        produtos = [
            ('Lapiseira Cis 0.7mm', 8.50), ('Grafite Faber-Castell 0.7', 4.00),
            ('Caderno Tilibra 10 Matérias', 35.90), ('Caderno Brochura', 12.00),
            ('Resma Chamex A4 500 fls', 29.90), ('Caneta BIC (Azul/Preta)', 2.50),
            ('Kit Stabilo Boss (6 cores)', 65.00), ('Mochila Faber-Castell', 189.90),
            ('Estojo Escolar DAC', 45.00), ('Borracha Mercur Record', 3.00),
            ('Apontador com Depósito', 7.50), ('Tinta Guache Acrilex', 15.00),
            ('Pincel Chato Tigre', 6.50), ('Fita Durex Larga 3M', 18.00),
            ('Cola Tenaz 90g', 5.50), ('Tesoura Maped', 11.00),
            ('Calculadora Casio', 45.00), ('Bloco Post-it 3M', 14.90),
            ('Pasta Sanfonada DAC', 22.00), ('Caderno Inteligente', 32.00),
            ('Cartolina Escolar', 1.50), ('Folha de EVA', 2.00)
        ]

        # Compras de Estoque ajustadas para representar ~40% do faturamento
        compras_estoque = [
            ('Tilibra S.A.', 'Lote Cadernos (Atacado)', 4500.00),
            ('Faber-Castell', 'Lote Lápis, Borrachas e Estojos', 3800.00),
            ('Distribuidora Chamex', 'Palete Papel Sulfite A4', 5200.00),
            ('Cis / Sertic', 'Reposição Lapiseiras e Canetas', 1900.00),
            ('Acrilex', 'Tintas e Materiais de Arte', 1100.00),
            ('DAC', 'Pastas e Organizadores', 1500.00)
        ]

        notas_geradas = []
        data_atual = date(2026, 1, 1)
        data_fim = date(2026, 4, 30)
        
        while data_atual <= data_fim:
            data_str = data_atual.strftime('%Y-%m-%d')
            
            # --- VENDAS DIÁRIAS ---
            if data_atual.weekday() != 6:
                qtd_vendas = random.randint(50, 130) # Vendas levemente mais altas
                for _ in range(qtd_vendas):
                    produto = random.choice(produtos)
                    valor_venda = round(produto[1] * random.uniform(0.95, 1.05), 2)
                    notas_geradas.append((data_str, valor_venda, 'Cliente Balcão', 'Venda', 'Entrada', produto[0], ''))
                    
                if random.random() < 0.10:
                    notas_geradas.append((data_str, random.randint(300, 1200), 'Cliente Corporativo', 'Venda B2B', 'Entrada', 'Material de Escritório', ''))

                # Despesas operacionais diárias menores
                if random.random() < 0.30: 
                    notas_geradas.append((data_str, random.randint(25, 45), 'Loggi / Correios', 'Logística', 'Saída', 'Frete de Entregas', ''))

            # --- DESPESAS SEMANAIS ---
            if data_atual.weekday() == 5:
                notas_geradas.append((data_str, random.randint(80, 150), 'Mercado Assaí', 'Despesa Operacional', 'Saída', 'Material de Limpeza e Copa', ''))
            
            if data_atual.day == 28:
                notas_geradas.append((data_str, 50.00, 'Banco Itaú', 'Taxas Bancárias', 'Saída', 'Manutenção de Conta', ''))

            # --- COMPRAS DE ESTOQUE (1x por semana) ---
            if data_atual.weekday() == 1:
                fornecedor = random.choice(compras_estoque)
                notas_geradas.append((data_str, fornecedor[2], fornecedor[0], 'Compra de Estoque', 'Saída', fornecedor[1], ''))

            # --- DESPESAS MENSAIS (Ajustadas para garantir 20-25% de lucro) ---
            if data_atual.day == 5:
                notas_geradas.append((data_str, 3000.00, 'Imobiliária Centro', 'Despesa Fixa', 'Saída', 'Aluguel Loja Física', ''))
                notas_geradas.append((data_str, 6500.00, 'Folha de Pagamento', 'Despesa Fixa', 'Saída', 'Salários (Equipe Enxuta)', ''))
                notas_geradas.append((data_str, 120.00, 'Provedor Claro', 'Despesa Fixa', 'Saída', 'Internet Loja', ''))
                
            if data_atual.day == 20:
                luz = round(random.uniform(350.00, 500.00), 2)
                notas_geradas.append((data_str, luz, 'Enel', 'Despesa Fixa', 'Saída', 'Conta de Energia', ''))
                notas_geradas.append((data_str, 85.00, 'Companhia de Água', 'Despesa Fixa', 'Saída', 'Conta de Água', ''))
                notas_geradas.append((data_str, 3500.00, 'Receita Federal', 'Impostos', 'Saída', 'DAS / ICMS', ''))
                
            data_atual += timedelta(days=1)

        cursor.executemany('''
            INSERT INTO notas (data, valor, estabelecimento, categoria, tipo, descricao, arquivo_xml) 
            VALUES (?,?,?,?,?,?,?)
        ''', notas_geradas)
        print(f"Sucesso! {len(notas_geradas)} registros gerados.")
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()