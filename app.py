import customtkinter as ctk
from tkinter import filedialog, messagebox
import sqlite3
import xml.etree.ElementTree as ET
import os
from datetime import datetime

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

def validar_data_emissao(data_str):
    """ BUG 1: Aceita datas no futuro. """
    try:
        dt = datetime.strptime(data_str, '%d/%m/%Y')
        return True 
    except ValueError:
        return False

def validar_valor_nota(valor_str):
    """ BUG 2: Aceita valores negativos ou zero. """
    try:
        v = float(valor_str.replace(',', '.'))
        return True
    except ValueError:
        return False

def calcular_resumo_financeiro(registros):
    """ BUG 3: Retorna tudo zerado. """
    resumo = {'entradas': 0.0, 'saidas': 0.0, 'saldo': 0.0}
    for r in registros:
        pass 
    return resumo

# =================================================================

def data_para_db(data_str):
    try: return datetime.strptime(data_str, '%d/%m/%Y').strftime('%Y-%m-%d')
    except: return None

def data_para_ui(data_str):
    try: return datetime.strptime(data_str, '%Y-%m-%d').strftime('%d/%m/%Y')
    except: return data_str

class NfeSystem(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Controle Fiscal TechStore")
        self.attributes("-fullscreen", True)
        self.bind("<Escape>", lambda e: self.destroy())
        self.current_file_path = "" 
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.show_login_screen()

    def show_login_screen(self):
        self.login_frame = ctk.CTkFrame(self, width=400, height=450, corner_radius=20)
        self.login_frame.place(relx=0.5, rely=0.5, anchor="center")
        ctk.CTkLabel(self.login_frame, text="Controle Fiscal", font=("Arial", 28, "bold")).pack(pady=40)
        self.user = ctk.CTkEntry(self.login_frame, placeholder_text="Usuário", width=280, height=45)
        self.user.pack(pady=10)
        self.pwd = ctk.CTkEntry(self.login_frame, placeholder_text="Senha", show="*", width=280, height=45)
        self.pwd.pack(pady=10)
        ctk.CTkButton(self.login_frame, text="ENTRAR", command=self.login, width=280, height=45).pack(pady=30)

    def login(self):
        if self.user.get() == "admin" and self.pwd.get() == "admin":
            self.login_frame.destroy()
            self.setup_dashboard()
        else:
            messagebox.showerror("Erro", "Login Inválido")

    def setup_dashboard(self):
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        ctk.CTkLabel(self.sidebar, text="MENU", font=("Arial", 20, "bold")).pack(pady=30)
        ctk.CTkButton(self.sidebar, text="Registrar Operação", command=lambda: self.show_page("cadastrar")).pack(pady=10, padx=20)
        ctk.CTkButton(self.sidebar, text="Livro Caixa / NF-e", command=lambda: self.show_page("visualizar")).pack(pady=10, padx=20)
        ctk.CTkButton(self.sidebar, text="Sair", fg_color="red", command=self.destroy).pack(side="bottom", pady=20)

        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.grid(row=0, column=1, sticky="nsew", padx=30, pady=30)
        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_rowconfigure(0, weight=1) # <- CORREÇÃO DO LAYOUT AQUI!

        self.pages = {}
        self.setup_cadastrar()
        self.setup_visualizar()
        self.show_page("visualizar")

    def show_page(self, name):
        for p in self.pages.values(): p.grid_remove()
        self.pages[name].grid(row=0, column=0, sticky="nsew")
        if name == "visualizar": self.carregar_notas_cadastradas()

    def setup_cadastrar(self):
        p = ctk.CTkFrame(self.container)
        self.pages["cadastrar"] = p
        ctk.CTkLabel(p, text="Nova Operação / Anexar NF-e", font=("Arial", 24, "bold")).pack(pady=20)
        
        file_frame = ctk.CTkFrame(p, fg_color="#2B2B2B", corner_radius=10)
        file_frame.pack(pady=10, padx=40, fill="x")
        ctk.CTkButton(file_frame, text="Carregar Arquivo XML", command=self.carregar_arquivo, fg_color="#2E7D32", hover_color="#1B5E20").pack(side="left", padx=20, pady=15)
        self.lbl_arquivo = ctk.CTkLabel(file_frame, text="Nenhum arquivo selecionado", text_color="gray")
        self.lbl_arquivo.pack(side="left", padx=10, pady=15)
        
        self.ent_tipo = ctk.CTkOptionMenu(p, values=["Entrada", "Saída"], width=400)
        self.ent_tipo.pack(pady=10)
        self.ent_tipo.set("Entrada")
        self.ent_est = ctk.CTkEntry(p, placeholder_text="Cliente / Fornecedor", width=400)
        self.ent_est.pack(pady=10)
        self.ent_data = ctk.CTkEntry(p, placeholder_text="Data (DD/MM/YYYY)", width=400)
        self.ent_data.pack(pady=10)
        self.ent_val = ctk.CTkEntry(p, placeholder_text="Valor (R$)", width=400)
        self.ent_val.pack(pady=10)
        self.ent_cat = ctk.CTkEntry(p, placeholder_text="Categoria (Ex: Venda, Despesa)", width=400)
        self.ent_cat.pack(pady=10)
        
        ctk.CTkButton(p, text="Salvar Registro", command=self.salvar, width=200).pack(pady=20)

    def carregar_arquivo(self):
        file_path = filedialog.askopenfilename(filetypes=[("Arquivos XML", "*.xml")])
        if not file_path: return
        self.current_file_path = file_path
        self.lbl_arquivo.configure(text=os.path.basename(file_path), text_color="white")
        try:
            tree = ET.parse(file_path)
            ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
            estabelecimento = tree.find('.//nfe:emit/nfe:xNome', ns)
            data = tree.find('.//nfe:dhEmi', ns)
            valor = tree.find('.//nfe:vNF', ns)
            if estabelecimento is not None:
                self.ent_est.delete(0, 'end'); self.ent_est.insert(0, estabelecimento.text)
            if data is not None:
                self.ent_data.delete(0, 'end'); self.ent_data.insert(0, data_para_ui(data.text.split('T')[0])) 
            if valor is not None:
                self.ent_val.delete(0, 'end'); self.ent_val.insert(0, valor.text)
            messagebox.showinfo("Sucesso", "Dados extraídos do XML!")
        except:
            messagebox.showwarning("Aviso", "Não foi possível extrair dados.")

    def salvar(self):
        if not validar_data_emissao(self.ent_data.get()):
            return messagebox.showerror("Erro", "Data inválida ou no futuro!")
        if not validar_valor_nota(self.ent_val.get()):
            return messagebox.showerror("Erro", "O valor deve ser positivo (maior que zero)!")
            
        dt = data_para_db(self.ent_data.get())
        if not self.ent_est.get(): return messagebox.showerror("Erro", "Preencha o estabelecimento.")
            
        try:
            conn = sqlite3.connect('notas_fiscais.db')
            conn.execute("INSERT INTO notas (data, valor, estabelecimento, categoria, tipo, arquivo_xml) VALUES (?,?,?,?,?,?)",
                         (dt, float(self.ent_val.get().replace(',','.')), self.ent_est.get(), self.ent_cat.get(), self.ent_tipo.get(), self.current_file_path))
            conn.commit()
            conn.close()
            messagebox.showinfo("Sucesso", "Salvo!")
            self.show_page("visualizar")
        except:
            messagebox.showerror("Erro", "Erro ao gravar.")

    def setup_visualizar(self):
        p = ctk.CTkFrame(self.container, fg_color="transparent")
        self.pages["visualizar"] = p
        
        header = ctk.CTkFrame(p, fg_color="transparent")
        header.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(header, text="Livro Caixa", font=("Arial", 26, "bold")).pack(side="left", padx=(0,20))
        self.f_txt = ctk.CTkEntry(header, placeholder_text="Busca...", width=200)
        self.f_txt.pack(side="left", padx=5)
        self.f_ini = ctk.CTkEntry(header, placeholder_text="Início (DD/MM/YYYY)", width=140)
        self.f_ini.pack(side="left", padx=5)
        self.f_fim = ctk.CTkEntry(header, placeholder_text="Fim (DD/MM/YYYY)", width=140)
        self.f_fim.pack(side="left", padx=5)
        ctk.CTkButton(header, text="Filtrar", width=100, command=self.carregar_notas_cadastradas).pack(side="left", padx=10)
        
        resumo_frame = ctk.CTkFrame(header, fg_color="transparent")
        resumo_frame.pack(side="right")
        self.lbl_in = ctk.CTkLabel(resumo_frame, text="Entradas: R$ 0.00", text_color="#43A047", font=("Arial", 14, "bold"))
        self.lbl_in.pack(side="left", padx=10)
        self.lbl_out = ctk.CTkLabel(resumo_frame, text="Saídas: R$ 0.00", text_color="#E53935", font=("Arial", 14, "bold"))
        self.lbl_out.pack(side="left", padx=10)
        self.lbl_saldo = ctk.CTkLabel(resumo_frame, text="Saldo: R$ 0.00", font=("Arial", 18, "bold"))
        self.lbl_saldo.pack(side="left", padx=10)

        self.scroll = ctk.CTkScrollableFrame(p, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True)

    def carregar_notas_cadastradas(self):
        for w in self.scroll.winfo_children(): w.destroy()
        conn = sqlite3.connect('notas_fiscais.db')
        cursor = conn.cursor()
        
        query = "SELECT * FROM notas WHERE 1=1"
        params = []
        if self.f_txt.get(): 
            query += " AND (estabelecimento LIKE ? OR categoria LIKE ?)"
            params.extend(['%'+self.f_txt.get()+'%', '%'+self.f_txt.get()+'%'])
        if self.f_ini.get():
            dt = data_para_db(self.f_ini.get())
            if dt: query += " AND data >= ?"; params.append(dt)
        if self.f_fim.get():
            dt = data_para_db(self.f_fim.get())
            if dt: query += " AND data <= ?"; params.append(dt)
        
        cursor.execute(query + " ORDER BY data DESC", params)
        registros = cursor.fetchall()
        conn.close()

        resumo = calcular_resumo_financeiro(registros)
        self.lbl_in.configure(text=f"Entradas: R$ {resumo['entradas']:.2f}")
        self.lbl_out.configure(text=f"Saídas: R$ {resumo['saidas']:.2f}")
        cor_saldo = "yellow" if resumo['saldo'] >= 0 else "red"
        self.lbl_saldo.configure(text=f"Saldo: R$ {resumo['saldo']:.2f}", text_color=cor_saldo)

        for r in registros:
            card = ctk.CTkFrame(self.scroll, fg_color="#2B2B2B", height=50)
            card.pack(fill="x", pady=2, padx=5)
            ctk.CTkLabel(card, text=data_para_ui(r[1]), width=100).pack(side="left", padx=10)
            ctk.CTkLabel(card, text=r[3], font=("Arial", 13, "bold"), width=250, anchor="w").pack(side="left", padx=10)
            ctk.CTkLabel(card, text=r[4], width=150).pack(side="left", padx=10)
            cor = "#43A047" if r[5] == "Entrada" else "#E53935"
            sinal = "+" if r[5] == "Entrada" else "-"
            ctk.CTkLabel(card, text=f"{sinal} R$ {r[2]:.2f}", text_color=cor, font=("Arial", 13, "bold")).pack(side="right", padx=20)

if __name__ == "__main__":
    app = NfeSystem()
    app.mainloop()