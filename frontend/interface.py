import customtkinter as ctk
from tkinter import filedialog
import os
import json
from collections import defaultdict
from datetime import datetime
import calendar
from urllib import error, parse, request
import pandas as pd
from backend.services import validar_data_emissao, validar_valor_nota

# --- CONFIGURAÇÃO PREMIUM ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

BG_COLOR = "#0F1015"          
CARD_COLOR = "#1C1D22"        
INPUT_BG = "#23252B"          
SIDEBAR_COLOR = "#15161A"     
ACCENT_COLOR = "#3B82F6"      
HOVER_COLOR = "#2563EB"       
SUCCESS_COLOR = "#10B981"     
DANGER_COLOR = "#EF4444"      
TEXT_GRAY = "#9CA3AF"         
BORDER_COLOR = "#2A2B30"      
API_BASE_URL = "http://127.0.0.1:5000/api"

# Larguras da Tabela
COL0_W = 160  
COL2_W = 190  
COL3_W = 220  
COL4_W = 160  

class CTkCalendar(ctk.CTkToplevel):
    def __init__(self, parent, target_entry):
        super().__init__(parent)
        self.target = target_entry
        self.title("Selecione a Data")
        
        win_w = 280; win_h = 320
        self.geometry(f"{win_w}x{win_h}")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.configure(fg_color=CARD_COLOR)
        
        x = self.winfo_pointerx(); y = self.winfo_pointery()
        screen_w = self.winfo_screenwidth(); screen_h = self.winfo_screenheight()
        if (x + win_w) > screen_w: x = screen_w - win_w - 10  
        if (y + win_h) > screen_h: y = screen_h - win_h - 40  
            
        self.geometry(f"+{x}+{y}")
        self.curr_year = datetime.now().year
        self.curr_month = datetime.now().month
        self.meses_ptbr = ["", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
        
        self.setup_ui()

    def setup_ui(self):
        for w in self.winfo_children(): w.destroy()
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(15, 10))

        ctk.CTkButton(header, text="<", width=30, fg_color="transparent", hover_color=BORDER_COLOR, command=self.prev_month).pack(side="left", padx=10)
        self.lbl_month = ctk.CTkLabel(header, text=f"{self.meses_ptbr[self.curr_month]} {self.curr_year}", font=("Segoe UI", 14, "bold"))
        self.lbl_month.pack(side="left", expand=True)
        ctk.CTkButton(header, text=">", width=30, fg_color="transparent", hover_color=BORDER_COLOR, command=self.next_month).pack(side="right", padx=10)

        days_frame = ctk.CTkFrame(self, fg_color="transparent")
        days_frame.pack(fill="x", padx=10)
        for d in ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"]:
            ctk.CTkLabel(days_frame, text=d, text_color=TEXT_GRAY, width=34, font=("Segoe UI", 11)).pack(side="left", padx=1)

        self.grid_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.grid_frame.pack(fill="both", expand=True, padx=10, pady=5)
        self.populate_grid()

    def populate_grid(self):
        cal = calendar.Calendar(firstweekday=6)
        month_days = cal.monthdayscalendar(self.curr_year, self.curr_month)

        for r, week in enumerate(month_days):
            for c, day in enumerate(week):
                if day != 0:
                    btn = ctk.CTkButton(self.grid_frame, text=str(day), width=34, height=34,
                                        fg_color="transparent", hover_color=ACCENT_COLOR, font=("Segoe UI", 13),
                                        command=lambda d=day: self.select_day(d))
                    btn.grid(row=r, column=c, padx=1, pady=1)

    def prev_month(self):
        self.curr_month -= 1
        if self.curr_month == 0: self.curr_month = 12; self.curr_year -= 1
        self.setup_ui()

    def next_month(self):
        self.curr_month += 1
        if self.curr_month == 13: self.curr_month = 1; self.curr_year += 1
        self.setup_ui()

    def select_day(self, day):
        data_formatada = f"{day:02d}/{self.curr_month:02d}/{self.curr_year}"
        self.target.delete(0, 'end')
        self.target.insert(0, data_formatada)
        self.destroy()

class NfeSystem(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Papelaria Central - Controle Fiscal")
        self.attributes("-fullscreen", True)
        self.bind("<Escape>", lambda e: self.destroy())
        self.configure(fg_color=BG_COLOR)
        
        self.current_file_path = "" 
        self.dados_relatorio = []
        self.user_level = ""
        
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.show_login_screen()

    def api_request(self, metodo, endpoint, dados=None, params=None):
        url = f"{API_BASE_URL}{endpoint}"
        if params:
            params_limpos = {k: v for k, v in params.items() if v}
            if params_limpos:
                url += "?" + parse.urlencode(params_limpos)

        payload = None
        headers = {"Content-Type": "application/json"}
        if dados is not None:
            payload = json.dumps(dados).encode("utf-8")

        req = request.Request(url, data=payload, headers=headers, method=metodo)
        try:
            with request.urlopen(req, timeout=5) as resp:
                corpo = resp.read().decode("utf-8")
                return json.loads(corpo) if corpo else {}
        except error.HTTPError as e:
            corpo = e.read().decode("utf-8")
            try:
                detalhe = json.loads(corpo).get("erro", corpo)
            except json.JSONDecodeError:
                detalhe = corpo or str(e)
            raise RuntimeError(detalhe) from e
        except error.URLError as e:
            raise RuntimeError("API indisponível. Verifique se o servidor Flask está em execução.") from e

    def buscar_notas_api(self, busca="", inicio="", fim=""):
        return self.api_request(
            "GET",
            "/notas",
            params={"busca": busca, "inicio": inicio, "fim": fim},
        )

    def show_toast(self, mensagem, tipo="sucesso"):
        cor_fundo = SUCCESS_COLOR if tipo == "sucesso" else DANGER_COLOR
        icone = "✅ " if tipo == "sucesso" else "⚠️ "
        toast = ctk.CTkFrame(self, fg_color=cor_fundo, corner_radius=8)
        toast.place(relx=0.98, rely=0.95, anchor="se")
        ctk.CTkLabel(toast, text=icone + mensagem, text_color="white", font=("Segoe UI", 14, "bold")).pack(padx=20, pady=12)
        self.after(3000, toast.destroy)

    # --- TELA DE LOGIN 100% TIPOGRÁFICA E CENTRALIZADA ---
    def show_login_screen(self):
        self.login_frame = ctk.CTkFrame(self, width=420, height=480, corner_radius=15, fg_color=CARD_COLOR, border_width=1, border_color=BORDER_COLOR)
        self.login_frame.place(relx=0.5, rely=0.5, anchor="center")
        self.login_frame.grid_propagate(False)
        
        accent_pill = ctk.CTkFrame(self.login_frame, width=60, height=6, fg_color=ACCENT_COLOR, corner_radius=3)
        accent_pill.pack(pady=(25, 0))
        
        # Agrupamento do título (Papelaria Central) com 2 cores
        title_frame = ctk.CTkFrame(self.login_frame, fg_color="transparent")
        title_frame.pack(pady=(45, 35))
        
        logo_label = ctk.CTkFrame(title_frame, fg_color="transparent")
        logo_label.pack()
        ctk.CTkLabel(logo_label, text="Papelaria", font=("Segoe UI", 32, "bold"), text_color="white").pack(side="left")
        ctk.CTkLabel(logo_label, text="Central", font=("Segoe UI", 32, "bold"), text_color=ACCENT_COLOR).pack(side="left", padx=(6, 0))
        
        ctk.CTkLabel(title_frame, text="Acesse o seu painel de controle", text_color=TEXT_GRAY, font=("Segoe UI", 13)).pack(pady=(8, 0))
        
        self.user = ctk.CTkEntry(self.login_frame, placeholder_text="Usuário", width=340, height=50, border_width=1, border_color=BORDER_COLOR, fg_color=INPUT_BG, corner_radius=8, font=("Segoe UI", 14))
        self.user.pack(pady=(0, 15))
        
        self.pwd = ctk.CTkEntry(self.login_frame, placeholder_text="Senha", show="•", width=340, height=50, border_width=1, border_color=BORDER_COLOR, fg_color=INPUT_BG, corner_radius=8, font=("Segoe UI", 14))
        self.pwd.pack(pady=(0, 30))
        
        btn_login = ctk.CTkButton(self.login_frame, text="ENTRAR", command=self.login, width=340, height=50, fg_color=ACCENT_COLOR, hover_color=HOVER_COLOR, font=("Segoe UI", 15, "bold"), corner_radius=8)
        btn_login.pack()

    def login(self):
        usr = self.user.get()
        pwd = self.pwd.get()

        try:
            usuario = self.api_request(
                "POST",
                "/login",
                {"username": usr, "password": pwd},
            )
            self.user_level = usuario["nivel"]
            self.show_toast(f"Bem-vindo! Acesso: {self.user_level}", "sucesso")
            self.login_frame.destroy()
            self.setup_dashboard()
        except Exception as e:
            self.show_toast(f"Erro no login: {e}", "erro")

    # --- SIDEBAR REDESENHADA ---
    def setup_dashboard(self):
        self.sidebar = ctk.CTkFrame(self, width=240, corner_radius=0, fg_color=SIDEBAR_COLOR)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(5, weight=1)
        
        # Identidade visual na sidebar
        brand_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand_frame.pack(pady=(40, 35))
        
        logo_box = ctk.CTkFrame(brand_frame, fg_color="transparent")
        logo_box.pack()
        ctk.CTkLabel(logo_box, text="Papelaria", font=("Segoe UI", 24, "bold"), text_color="white").pack(side="left")
        ctk.CTkLabel(logo_box, text=".", font=("Segoe UI", 24, "bold"), text_color=ACCENT_COLOR).pack(side="left", padx=(2, 0))
        
        # Badge de usuário estilo pílula
        badge = ctk.CTkFrame(brand_frame, fg_color=INPUT_BG, corner_radius=12, border_width=1, border_color=BORDER_COLOR)
        badge.pack(pady=(12, 0), ipadx=12, ipady=4)
        ctk.CTkLabel(badge, text=self.user_level.upper(), text_color=ACCENT_COLOR, font=("Segoe UI", 10, "bold")).pack()
        
        self.btn_nav_cadastrar = ctk.CTkButton(self.sidebar, text="📝 Registrar Operação", anchor="w", height=45, fg_color="transparent", font=("Segoe UI", 15), command=lambda: self.show_page("cadastrar"))
        self.btn_nav_cadastrar.pack(fill="x", padx=15, pady=5)
        
        self.btn_nav_visualizar = ctk.CTkButton(self.sidebar, text="📊 Resumo Caixa", anchor="w", height=45, fg_color="transparent", font=("Segoe UI", 15), command=lambda: self.show_page("visualizar"))
        self.btn_nav_visualizar.pack(fill="x", padx=15, pady=5)

        if self.user_level in ["Administrador", "Gerente"]:
            self.btn_nav_relatorios = ctk.CTkButton(self.sidebar, text="📈 Relatórios / Excel", anchor="w", height=45, fg_color="transparent", font=("Segoe UI", 15), command=lambda: self.show_page("relatorios"))
            self.btn_nav_relatorios.pack(fill="x", padx=15, pady=5)
        else:
            self.btn_nav_relatorios = None

        if self.user_level == "Administrador":
            self.btn_nav_gerenciar = ctk.CTkButton(self.sidebar, text="🛠 Gerenciar Operações", anchor="w", height=45, fg_color="transparent", font=("Segoe UI", 15), command=lambda: self.show_page("gerenciar"))
            self.btn_nav_gerenciar.pack(fill="x", padx=15, pady=5)
        else:
            self.btn_nav_gerenciar = None
        
        btn_sair = ctk.CTkButton(self.sidebar, text="🚪 Sair do Sistema", anchor="w", height=45, fg_color="transparent", hover_color="#3F0000", text_color=DANGER_COLOR, font=("Segoe UI", 15), command=self.destroy)
        btn_sair.pack(side="bottom", fill="x", padx=15, pady=20)

        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.grid(row=0, column=1, sticky="nsew", padx=40, pady=40)
        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_rowconfigure(0, weight=1)

        self.pages = {}
        self.setup_cadastrar()
        self.setup_visualizar()
        if self.user_level in ["Administrador", "Gerente"]:
            self.setup_relatorios()
        if self.user_level == "Administrador":
            self.setup_gerenciar()
            
        self.show_page("visualizar", carregar=False)
        self.after(100, self.carregar_notas_cadastradas)

    def show_page(self, name, carregar=True):
        for p in self.pages.values(): p.grid_remove()
        self.pages[name].grid(row=0, column=0, sticky="nsew")
        
        self.btn_nav_cadastrar.configure(fg_color=CARD_COLOR if name == "cadastrar" else "transparent")
        self.btn_nav_visualizar.configure(fg_color=CARD_COLOR if name == "visualizar" else "transparent")
        
        if self.btn_nav_relatorios:
            self.btn_nav_relatorios.configure(fg_color=CARD_COLOR if name == "relatorios" else "transparent")

        if self.btn_nav_gerenciar:
            self.btn_nav_gerenciar.configure(fg_color=CARD_COLOR if name == "gerenciar" else "transparent")
        
        if name == "visualizar" and carregar: self.carregar_notas_cadastradas()
        if name == "gerenciar" and carregar: self.carregar_operacoes_admin()

    def open_calendar(self, entry_widget):
        CTkCalendar(self, entry_widget)

    def setup_cadastrar(self):
        p = ctk.CTkFrame(self.container, fg_color="transparent")
        self.pages["cadastrar"] = p
        
        ctk.CTkLabel(p, text="Nova Operação", font=("Segoe UI", 32, "bold")).pack(anchor="w", pady=(0, 30))
        form_container = ctk.CTkFrame(p, fg_color=CARD_COLOR, corner_radius=15, border_width=1, border_color=BORDER_COLOR)
        form_container.pack(fill="x", ipady=20)
        
        file_frame = ctk.CTkFrame(form_container, fg_color="transparent")
        file_frame.pack(pady=20, padx=40, fill="x")
        ctk.CTkLabel(file_frame, text="Automatize preenchendo via XML:", text_color=TEXT_GRAY).pack(side="left", padx=(0, 20))
        ctk.CTkButton(file_frame, text="📂 Carregar Arquivo XML", command=self.carregar_arquivo, fg_color=SUCCESS_COLOR, hover_color="#059669", font=("Segoe UI", 13, "bold")).pack(side="left")
        self.lbl_arquivo = ctk.CTkLabel(file_frame, text="Nenhum arquivo", text_color=TEXT_GRAY)
        self.lbl_arquivo.pack(side="left", padx=20)
        
        self.ent_tipo = ctk.CTkOptionMenu(form_container, values=["Entrada", "Saída"], width=500, height=45, fg_color=ACCENT_COLOR, button_color=HOVER_COLOR)
        self.ent_tipo.pack(pady=10)
        
        self.ent_est = ctk.CTkEntry(form_container, placeholder_text="Cliente / Fornecedor", width=500, height=45)
        self.ent_est.pack(pady=10)
        
        data_frame = ctk.CTkFrame(form_container, fg_color="transparent")
        data_frame.pack(pady=10)
        self.ent_data = ctk.CTkEntry(data_frame, placeholder_text="Data de Emissão (DD/MM/YYYY)", width=450, height=45)
        self.ent_data.pack(side="left")
        ctk.CTkButton(data_frame, text="📅", width=45, height=45, fg_color=BORDER_COLOR, hover_color=ACCENT_COLOR, command=lambda: self.open_calendar(self.ent_data)).pack(side="left", padx=(5, 0))
        
        self.ent_val = ctk.CTkEntry(form_container, placeholder_text="Valor Total (R$)", width=500, height=45)
        self.ent_val.pack(pady=10)
        self.ent_cat = ctk.CTkEntry(form_container, placeholder_text="Categoria (Ex: Venda, Despesa, Estoque)", width=500, height=45)
        self.ent_cat.pack(pady=10)
        self.ent_desc = ctk.CTkEntry(form_container, placeholder_text="Descrição (Ex: 3x Cadernos, Conta de Luz)", width=500, height=45)
        self.ent_desc.pack(pady=10)
        
        ctk.CTkButton(form_container, text="💾 Salvar Registro", command=self.salvar, width=500, height=45, fg_color=ACCENT_COLOR, hover_color=HOVER_COLOR, font=("Segoe UI", 14, "bold")).pack(pady=(20, 0))

    def carregar_arquivo(self):
        file_path = filedialog.askopenfilename(filetypes=[("Arquivos XML", "*.xml")])
        if not file_path: return
        self.current_file_path = file_path
        self.lbl_arquivo.configure(text=os.path.basename(file_path), text_color="white")
        self.show_toast("Arquivo anexado com sucesso!", "sucesso")

    def salvar(self):
        if not validar_data_emissao(self.ent_data.get()): return self.show_toast("Data inválida ou no futuro!", "erro")
        if not validar_valor_nota(self.ent_val.get()): return self.show_toast("O valor deve ser positivo!", "erro")
        if not self.ent_est.get(): return self.show_toast("Preencha o estabelecimento.", "erro")
            
        try:
            self.api_request(
                "POST",
                "/notas",
                {
                    "data": self.ent_data.get(),
                    "valor": self.ent_val.get(),
                    "estabelecimento": self.ent_est.get(),
                    "categoria": self.ent_cat.get(),
                    "tipo": self.ent_tipo.get(),
                    "descricao": self.ent_desc.get(),
                    "arquivo_xml": self.current_file_path,
                },
            )
            self.show_toast("Registro salvo no Livro Caixa!", "sucesso")
            
            self.ent_est.delete(0, 'end'); self.ent_data.delete(0, 'end')
            self.ent_val.delete(0, 'end'); self.ent_cat.delete(0, 'end'); self.ent_desc.delete(0, 'end')
            self.lbl_arquivo.configure(text="Nenhum arquivo", text_color=TEXT_GRAY); self.current_file_path = ""
            self.carregar_notas_cadastradas()
        except Exception as e:
            self.show_toast(f"Erro ao salvar pela API: {e}", "erro")

    def limpar_filtros(self):
        self.f_txt.delete(0, 'end')
        self.f_ini.delete(0, 'end')
        self.f_fim.delete(0, 'end')
        self.carregar_notas_cadastradas()
        self.show_toast("Filtros removidos!", "sucesso")

    def setup_visualizar(self):
        p = ctk.CTkFrame(self.container, fg_color="transparent")
        self.pages["visualizar"] = p
        
        top_row = ctk.CTkFrame(p, fg_color="transparent")
        top_row.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(top_row, text="Resumo Caixa", font=("Segoe UI", 32, "bold")).pack(side="left")
        
        filtros_frame = ctk.CTkFrame(top_row, fg_color=CARD_COLOR, corner_radius=10, border_width=1, border_color=BORDER_COLOR)
        filtros_frame.pack(side="right")
        self.f_txt = ctk.CTkEntry(filtros_frame, placeholder_text="Buscar categoria...", width=220, border_width=0, fg_color=CARD_COLOR)
        self.f_txt.pack(side="left", padx=10, pady=5)
        ctk.CTkLabel(filtros_frame, text="|", text_color=BORDER_COLOR).pack(side="left")
        
        self.f_ini = ctk.CTkEntry(filtros_frame, placeholder_text="Início (Data)", width=100, border_width=0, fg_color=CARD_COLOR)
        self.f_ini.pack(side="left", padx=(10, 2), pady=5)
        ctk.CTkButton(filtros_frame, text="📅", width=30, fg_color="transparent", hover_color=BORDER_COLOR, command=lambda: self.open_calendar(self.f_ini)).pack(side="left")
        self.f_fim = ctk.CTkEntry(filtros_frame, placeholder_text="Fim (Data)", width=100, border_width=0, fg_color=CARD_COLOR)
        self.f_fim.pack(side="left", padx=(10, 2), pady=5)
        ctk.CTkButton(filtros_frame, text="📅", width=30, fg_color="transparent", hover_color=BORDER_COLOR, command=lambda: self.open_calendar(self.f_fim)).pack(side="left")
        
        ctk.CTkButton(filtros_frame, text="Filtrar", width=80, fg_color=ACCENT_COLOR, hover_color=HOVER_COLOR, command=self.carregar_notas_cadastradas).pack(side="right", padx=(5, 10), pady=5)
        ctk.CTkButton(filtros_frame, text="✖ Limpar", width=80, fg_color="transparent", border_width=1, border_color=BORDER_COLOR, text_color=TEXT_GRAY, hover_color=BORDER_COLOR, command=self.limpar_filtros).pack(side="right", padx=5, pady=5)

        self.resumo_frame = ctk.CTkFrame(p, fg_color="transparent")
        self.resumo_frame.pack(fill="x", pady=(0, 20))
        self.resumo_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
        def criar_card_resumo(parent, titulo, cor, col):
            card = ctk.CTkFrame(parent, fg_color=CARD_COLOR, corner_radius=8, height=90, border_width=1, border_color=BORDER_COLOR)
            card.grid(row=0, column=col, sticky="ew", padx=8)
            card.grid_propagate(False)
            linha = ctk.CTkFrame(card, fg_color=cor, height=4, corner_radius=0)
            linha.place(x=0, y=0, relwidth=1)
            ctk.CTkLabel(card, text=titulo, text_color=TEXT_GRAY, font=("Segoe UI", 12, "bold")).place(x=20, y=15)
            lbl_valor = ctk.CTkLabel(card, text="R$ 0.00", text_color="white", font=("Segoe UI", 26, "bold"))
            lbl_valor.place(x=20, y=40)
            return lbl_valor

        self.lbl_in = criar_card_resumo(self.resumo_frame, "⬇ TOTAL DE ENTRADAS", SUCCESS_COLOR, 0)
        self.lbl_out = criar_card_resumo(self.resumo_frame, "⬆ TOTAL DE SAÍDAS", DANGER_COLOR, 1)
        self.lbl_saldo = criar_card_resumo(self.resumo_frame, "💰 SALDO ACUMULADO", ACCENT_COLOR, 2)

        self.table_header = ctk.CTkFrame(p, fg_color="transparent", height=30)
        self.table_header.pack(fill="x", padx=(15, 30), pady=(5, 5)) 
        
        self.table_header.grid_columnconfigure(0, minsize=COL0_W, weight=0)
        self.table_header.grid_columnconfigure(1, weight=1)
        self.table_header.grid_columnconfigure(2, minsize=COL2_W, weight=0)
        self.table_header.grid_columnconfigure(3, minsize=COL3_W, weight=0)
        self.table_header.grid_columnconfigure(4, minsize=COL4_W, weight=0)
        
        font_header = ("Segoe UI", 12, "bold")
        ctk.CTkLabel(self.table_header, text="Data", text_color=TEXT_GRAY, font=font_header, anchor="w").grid(row=0, column=0, sticky="w", padx=(20, 10))
        ctk.CTkLabel(self.table_header, text="Tipo de Agrupamento", text_color=TEXT_GRAY, font=font_header, anchor="w").grid(row=0, column=1, sticky="w", padx=10)
        ctk.CTkLabel(self.table_header, text="Categoria", text_color=TEXT_GRAY, font=font_header, anchor="w").grid(row=0, column=2, sticky="w", padx=10)
        ctk.CTkLabel(self.table_header, text="Volume Diário", text_color=TEXT_GRAY, font=font_header, anchor="w").grid(row=0, column=3, sticky="w", padx=10)
        ctk.CTkLabel(self.table_header, text="Valor Total", text_color=TEXT_GRAY, font=font_header, anchor="e").grid(row=0, column=4, sticky="e", padx=(10, 25))

        self.scroll = ctk.CTkScrollableFrame(p, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True)

    def carregar_notas_cadastradas(self):
        for w in self.scroll.winfo_children(): w.destroy()
        try:
            notas = self.buscar_notas_api(
                busca=self.f_txt.get(),
                inicio=self.f_ini.get(),
                fim=self.f_fim.get(),
            )

            entradas = sum(n["valor"] for n in notas if n["tipo"] == "Entrada")
            saidas = sum(n["valor"] for n in notas if n["tipo"] == "Saída")
            resumo = {
                'entradas': entradas,
                'saidas': saidas,
                'saldo': entradas - saidas,
            }
            self.lbl_in.configure(text=f"R$ {resumo['entradas']:,.2f}")
            self.lbl_out.configure(text=f"R$ {resumo['saidas']:,.2f}")
            self.lbl_saldo.configure(text=f"R$ {resumo['saldo']:,.2f}", text_color=SUCCESS_COLOR if resumo['saldo'] >= 0 else DANGER_COLOR)

            limite = 100
            grupos = defaultdict(lambda: {"valor": 0.0, "quantidade": 0})
            for nota in notas:
                chave = (nota["data"], nota["categoria"], nota["tipo"])
                grupos[chave]["valor"] += nota["valor"]
                grupos[chave]["quantidade"] += 1

            registros_agrupados = sorted(
                [
                    {
                        "data": data,
                        "categoria": categoria,
                        "tipo": tipo,
                        "valor": dados["valor"],
                        "quantidade": dados["quantidade"],
                    }
                    for (data, categoria, tipo), dados in grupos.items()
                ],
                key=lambda item: datetime.strptime(item["data"], "%d/%m/%Y"),
                reverse=True,
            )

            for r in registros_agrupados[:limite]:
                card = ctk.CTkFrame(self.scroll, fg_color=CARD_COLOR, corner_radius=8, border_width=1, border_color=BORDER_COLOR)
                card.pack(fill="x", pady=4, padx=10) 
                
                card.grid_columnconfigure(0, minsize=COL0_W, weight=0)
                card.grid_columnconfigure(1, weight=1)
                card.grid_columnconfigure(2, minsize=COL2_W, weight=0)
                card.grid_columnconfigure(3, minsize=COL3_W, weight=0)
                card.grid_columnconfigure(4, minsize=COL4_W, weight=0)
                
                col0_frame = ctk.CTkFrame(card, fg_color="transparent")
                col0_frame.grid(row=0, column=0, sticky="w", padx=(20, 10), pady=12)
                
                # NOVO: Ícones tipo texto sólidos que não quebram o layout no Windows
                cor_icone = SUCCESS_COLOR if r["tipo"] == "Entrada" else DANGER_COLOR
                ctk.CTkLabel(col0_frame, text="●", text_color=cor_icone, font=("Segoe UI", 18)).pack(side="left", padx=(0, 10))
                ctk.CTkLabel(col0_frame, text=r["data"], text_color=TEXT_GRAY).pack(side="left")
                
                titulo = "Resumo Diário de Vendas" if r["tipo"] == "Entrada" else "Despesas / Compras"
                ctk.CTkLabel(card, text=titulo, font=("Segoe UI", 14, "bold"), anchor="w", text_color="white").grid(row=0, column=1, sticky="w", padx=10, pady=12)
                
                badge = ctk.CTkFrame(card, fg_color="transparent", border_width=1, border_color=BORDER_COLOR, corner_radius=6)
                badge.grid(row=0, column=2, sticky="w", padx=10, pady=12)
                ctk.CTkLabel(badge, text=r["categoria"], text_color="#D1D5DB", font=("Segoe UI", 11)).pack(padx=10, pady=2)
                
                qtd_texto = f"📦 {r['quantidade']} operação registrada" if r["quantidade"] == 1 else f"📦 {r['quantidade']} operações agrupadas"
                ctk.CTkLabel(card, text=qtd_texto, text_color=TEXT_GRAY, font=("Segoe UI", 12), anchor="w").grid(row=0, column=3, sticky="w", padx=10, pady=12)
                
                cor_valor = SUCCESS_COLOR if r["tipo"] == "Entrada" else DANGER_COLOR
                sinal = "+" if r["tipo"] == "Entrada" else "-"
                ctk.CTkLabel(card, text=f"{sinal} R$ {r['valor']:,.2f}", text_color=cor_valor, font=("Segoe UI", 15, "bold"), anchor="e").grid(row=0, column=4, sticky="e", padx=(10, 25), pady=12)
                
            if len(registros_agrupados) > limite:
                ctk.CTkLabel(self.scroll, text=f"⚠️ Exibindo os {limite} agrupamentos mais recentes.", text_color=TEXT_GRAY, font=("Segoe UI", 12, "italic")).pack(pady=15)
        except Exception as e:
            self.show_toast(f"Erro ao carregar notas: {e}", "erro")

    def setup_gerenciar(self):
        p = ctk.CTkFrame(self.container, fg_color="transparent")
        self.pages["gerenciar"] = p

        top_row = ctk.CTkFrame(p, fg_color="transparent")
        top_row.pack(fill="x", pady=(0, 20))
        ctk.CTkLabel(top_row, text="Gerenciar Operações", font=("Segoe UI", 32, "bold")).pack(side="left")

        filtros_frame = ctk.CTkFrame(top_row, fg_color=CARD_COLOR, corner_radius=10, border_width=1, border_color=BORDER_COLOR)
        filtros_frame.pack(side="right")
        self.g_txt = ctk.CTkEntry(filtros_frame, placeholder_text="Buscar operação...", width=260, border_width=0, fg_color=CARD_COLOR)
        self.g_txt.pack(side="left", padx=10, pady=5)
        ctk.CTkButton(filtros_frame, text="Buscar", width=80, fg_color=ACCENT_COLOR, hover_color=HOVER_COLOR, command=self.carregar_operacoes_admin).pack(side="left", padx=(5, 10), pady=5)

        self.admin_header = ctk.CTkFrame(p, fg_color="transparent", height=30)
        self.admin_header.pack(fill="x", padx=(15, 30), pady=(5, 5))
        self.admin_header.grid_columnconfigure(0, minsize=70, weight=0)
        self.admin_header.grid_columnconfigure(1, minsize=120, weight=0)
        self.admin_header.grid_columnconfigure(2, weight=1)
        self.admin_header.grid_columnconfigure(3, minsize=150, weight=0)
        self.admin_header.grid_columnconfigure(4, minsize=130, weight=0)
        self.admin_header.grid_columnconfigure(5, minsize=150, weight=0)

        font_header = ("Segoe UI", 12, "bold")
        ctk.CTkLabel(self.admin_header, text="ID", text_color=TEXT_GRAY, font=font_header, anchor="w").grid(row=0, column=0, sticky="w", padx=(20, 10))
        ctk.CTkLabel(self.admin_header, text="Data", text_color=TEXT_GRAY, font=font_header, anchor="w").grid(row=0, column=1, sticky="w", padx=10)
        ctk.CTkLabel(self.admin_header, text="Descrição", text_color=TEXT_GRAY, font=font_header, anchor="w").grid(row=0, column=2, sticky="w", padx=10)
        ctk.CTkLabel(self.admin_header, text="Categoria", text_color=TEXT_GRAY, font=font_header, anchor="w").grid(row=0, column=3, sticky="w", padx=10)
        ctk.CTkLabel(self.admin_header, text="Valor", text_color=TEXT_GRAY, font=font_header, anchor="e").grid(row=0, column=4, sticky="e", padx=10)
        ctk.CTkLabel(self.admin_header, text="Ações", text_color=TEXT_GRAY, font=font_header, anchor="e").grid(row=0, column=5, sticky="e", padx=(10, 25))

        self.scroll_admin = ctk.CTkScrollableFrame(p, fg_color="transparent")
        self.scroll_admin.pack(fill="both", expand=True)

    def carregar_operacoes_admin(self):
        if self.user_level != "Administrador":
            return self.show_toast("Apenas administradores podem gerenciar operações.", "erro")

        for w in self.scroll_admin.winfo_children():
            w.destroy()

        try:
            registros = self.buscar_notas_api(busca=self.g_txt.get())[:100]

            if not registros:
                ctk.CTkLabel(self.scroll_admin, text="Nenhuma operação encontrada.", text_color=TEXT_GRAY, font=("Segoe UI", 14)).pack(pady=30)
                return

            for r in registros:
                card = ctk.CTkFrame(self.scroll_admin, fg_color=CARD_COLOR, corner_radius=8, border_width=1, border_color=BORDER_COLOR)
                card.pack(fill="x", pady=4, padx=10)
                card.grid_columnconfigure(0, minsize=70, weight=0)
                card.grid_columnconfigure(1, minsize=120, weight=0)
                card.grid_columnconfigure(2, weight=1)
                card.grid_columnconfigure(3, minsize=150, weight=0)
                card.grid_columnconfigure(4, minsize=130, weight=0)
                card.grid_columnconfigure(5, minsize=150, weight=0)

                cor_valor = SUCCESS_COLOR if r["tipo"] == "Entrada" else DANGER_COLOR
                sinal = "+" if r["tipo"] == "Entrada" else "-"
                descricao = r["descricao"] or r["estabelecimento"]

                ctk.CTkLabel(card, text=str(r["id"]), text_color=TEXT_GRAY, anchor="w").grid(row=0, column=0, sticky="w", padx=(20, 10), pady=12)
                ctk.CTkLabel(card, text=r["data"], text_color=TEXT_GRAY, anchor="w").grid(row=0, column=1, sticky="w", padx=10, pady=12)
                ctk.CTkLabel(card, text=descricao, text_color="white", anchor="w").grid(row=0, column=2, sticky="w", padx=10, pady=12)
                ctk.CTkLabel(card, text=r["categoria"], text_color=TEXT_GRAY, anchor="w").grid(row=0, column=3, sticky="w", padx=10, pady=12)
                ctk.CTkLabel(card, text=f"{sinal} R$ {r['valor']:,.2f}", text_color=cor_valor, font=("Segoe UI", 13, "bold"), anchor="e").grid(row=0, column=4, sticky="e", padx=10, pady=12)

                acoes = ctk.CTkFrame(card, fg_color="transparent")
                acoes.grid(row=0, column=5, sticky="e", padx=(10, 20), pady=8)
                ctk.CTkButton(acoes, text="Editar", width=64, fg_color=ACCENT_COLOR, hover_color=HOVER_COLOR, command=lambda reg=r: self.abrir_editor_operacao(reg)).pack(side="left", padx=(0, 6))
                ctk.CTkButton(acoes, text="Excluir", width=64, fg_color=DANGER_COLOR, hover_color="#B91C1C", command=lambda nota_id=r["id"]: self.confirmar_exclusao_admin(nota_id)).pack(side="left")
        except Exception as e:
            self.show_toast(f"Erro ao carregar operações: {e}", "erro")

    def abrir_editor_operacao(self, registro):
        if self.user_level != "Administrador":
            return self.show_toast("Apenas administradores podem editar operações.", "erro")

        janela = ctk.CTkToplevel(self)
        janela.title(f"Editar Operação #{registro['id']}")
        janela.geometry("560x560")
        janela.resizable(False, False)
        janela.attributes("-topmost", True)
        janela.configure(fg_color=CARD_COLOR)

        ctk.CTkLabel(janela, text=f"Editar Operação #{registro['id']}", font=("Segoe UI", 24, "bold")).pack(anchor="w", padx=30, pady=(28, 18))

        ent_tipo = ctk.CTkOptionMenu(janela, values=["Entrada", "Saída"], width=500, height=42, fg_color=ACCENT_COLOR, button_color=HOVER_COLOR)
        ent_tipo.set(registro["tipo"])
        ent_tipo.pack(pady=8)

        ent_est = ctk.CTkEntry(janela, placeholder_text="Cliente / Fornecedor", width=500, height=42)
        ent_est.insert(0, registro["estabelecimento"] or "")
        ent_est.pack(pady=8)

        ent_data = ctk.CTkEntry(janela, placeholder_text="Data de Emissão (DD/MM/YYYY)", width=500, height=42)
        ent_data.insert(0, registro["data"])
        ent_data.pack(pady=8)

        ent_val = ctk.CTkEntry(janela, placeholder_text="Valor Total (R$)", width=500, height=42)
        ent_val.insert(0, str(registro["valor"]).replace(".", ","))
        ent_val.pack(pady=8)

        ent_cat = ctk.CTkEntry(janela, placeholder_text="Categoria", width=500, height=42)
        ent_cat.insert(0, registro["categoria"] or "")
        ent_cat.pack(pady=8)

        ent_desc = ctk.CTkEntry(janela, placeholder_text="Descrição", width=500, height=42)
        ent_desc.insert(0, registro["descricao"] or "")
        ent_desc.pack(pady=8)

        botoes = ctk.CTkFrame(janela, fg_color="transparent")
        botoes.pack(fill="x", padx=30, pady=(24, 0))
        ctk.CTkButton(botoes, text="Cancelar", width=150, fg_color="transparent", border_width=1, border_color=BORDER_COLOR, text_color=TEXT_GRAY, hover_color=BORDER_COLOR, command=janela.destroy).pack(side="left")
        ctk.CTkButton(
            botoes,
            text="Salvar Alterações",
            width=220,
            fg_color=ACCENT_COLOR,
            hover_color=HOVER_COLOR,
            command=lambda: self.atualizar_operacao_admin(
                registro["id"],
                ent_data.get(),
                ent_val.get(),
                ent_est.get(),
                ent_cat.get(),
                ent_tipo.get(),
                ent_desc.get(),
                registro["arquivo_xml"] or "",
                janela,
            ),
        ).pack(side="right")

    def atualizar_operacao_admin(self, nota_id, data, valor, estabelecimento, categoria, tipo, descricao, arquivo_xml, janela):
        if self.user_level != "Administrador":
            return self.show_toast("Apenas administradores podem editar operações.", "erro")
        if not validar_data_emissao(data):
            return self.show_toast("Data inválida ou no futuro!", "erro")
        if not validar_valor_nota(valor):
            return self.show_toast("O valor deve ser positivo!", "erro")
        if not estabelecimento:
            return self.show_toast("Preencha o estabelecimento.", "erro")

        try:
            self.api_request(
                "PUT",
                f"/notas/{nota_id}",
                {
                    "nivel": self.user_level,
                    "data": data,
                    "valor": valor,
                    "estabelecimento": estabelecimento,
                    "categoria": categoria,
                    "tipo": tipo,
                    "descricao": descricao,
                    "arquivo_xml": arquivo_xml,
                },
            )
            janela.destroy()
            self.carregar_operacoes_admin()
            self.carregar_notas_cadastradas()
            self.show_toast("Operação atualizada com sucesso!", "sucesso")
        except Exception as e:
            self.show_toast(f"Erro ao atualizar operação: {e}", "erro")

    def confirmar_exclusao_admin(self, nota_id):
        if self.user_level != "Administrador":
            return self.show_toast("Apenas administradores podem excluir operações.", "erro")

        janela = ctk.CTkToplevel(self)
        janela.title("Excluir Operação")
        janela.geometry("420x190")
        janela.resizable(False, False)
        janela.attributes("-topmost", True)
        janela.configure(fg_color=CARD_COLOR)

        ctk.CTkLabel(janela, text="Excluir operação?", font=("Segoe UI", 22, "bold")).pack(anchor="w", padx=28, pady=(28, 8))
        ctk.CTkLabel(janela, text=f"A operação #{nota_id} será removida do banco.", text_color=TEXT_GRAY, font=("Segoe UI", 13)).pack(anchor="w", padx=28)

        botoes = ctk.CTkFrame(janela, fg_color="transparent")
        botoes.pack(fill="x", padx=28, pady=(26, 0))
        ctk.CTkButton(botoes, text="Cancelar", width=130, fg_color="transparent", border_width=1, border_color=BORDER_COLOR, text_color=TEXT_GRAY, hover_color=BORDER_COLOR, command=janela.destroy).pack(side="left")
        ctk.CTkButton(botoes, text="Excluir", width=130, fg_color=DANGER_COLOR, hover_color="#B91C1C", command=lambda: self.excluir_operacao_admin(nota_id, janela)).pack(side="right")

    def excluir_operacao_admin(self, nota_id, janela):
        if self.user_level != "Administrador":
            return self.show_toast("Apenas administradores podem excluir operações.", "erro")

        try:
            self.api_request("DELETE", f"/notas/{nota_id}", {"nivel": self.user_level})
            janela.destroy()
            self.carregar_operacoes_admin()
            self.carregar_notas_cadastradas()
            self.show_toast("Operação excluída com sucesso!", "sucesso")
        except Exception as e:
            self.show_toast(f"Erro ao excluir operação: {e}", "erro")

    def setup_relatorios(self):
        p = ctk.CTkFrame(self.container, fg_color="transparent")
        self.pages["relatorios"] = p
        
        ctk.CTkLabel(p, text="Relatórios Analíticos e Exportação", font=("Segoe UI", 32, "bold")).pack(anchor="w", pady=(0, 20))
        
        filtro_frame = ctk.CTkFrame(p, fg_color=CARD_COLOR, corner_radius=10, border_width=1, border_color=BORDER_COLOR)
        filtro_frame.pack(fill="x", pady=10, ipady=15)
        
        linha1 = ctk.CTkFrame(filtro_frame, fg_color="transparent")
        linha1.pack(fill="x", padx=20, pady=(10, 5))
        
        ctk.CTkLabel(linha1, text="Tipo de Relatório:", text_color="white", font=("Segoe UI", 14)).pack(side="left", padx=(0, 10))
        self.rel_tipo = ctk.CTkOptionMenu(linha1, values=["Todos os Registros", "Apenas Vendas (Entradas)", "Apenas Despesas (Saídas)"], width=220, fg_color=INPUT_BG, button_color=BORDER_COLOR)
        self.rel_tipo.pack(side="left")
        
        ctk.CTkLabel(linha1, text="Buscar Produto/Fornecedor:", text_color="white", font=("Segoe UI", 14)).pack(side="left", padx=(30, 10))
        self.rel_txt = ctk.CTkEntry(linha1, placeholder_text="Ex: Chamex, Aluguel...", width=200, fg_color=INPUT_BG)
        self.rel_txt.pack(side="left")
        
        linha2 = ctk.CTkFrame(filtro_frame, fg_color="transparent")
        linha2.pack(fill="x", padx=20, pady=(5, 10))
        
        ctk.CTkLabel(linha2, text="Período de Análise:", text_color="white", font=("Segoe UI", 14)).pack(side="left", padx=(0, 10))
        self.rel_ini = ctk.CTkEntry(linha2, placeholder_text="Início (Data)", width=120, fg_color=INPUT_BG)
        self.rel_ini.pack(side="left")
        ctk.CTkButton(linha2, text="📅", width=30, fg_color="transparent", border_width=1, border_color=BORDER_COLOR, command=lambda: self.open_calendar(self.rel_ini)).pack(side="left", padx=(5, 20))
        
        self.rel_fim = ctk.CTkEntry(linha2, placeholder_text="Fim (Data)", width=120, fg_color=INPUT_BG)
        self.rel_fim.pack(side="left")
        ctk.CTkButton(linha2, text="📅", width=30, fg_color="transparent", border_width=1, border_color=BORDER_COLOR, command=lambda: self.open_calendar(self.rel_fim)).pack(side="left", padx=(5, 30))
        
        ctk.CTkButton(linha2, text="Gerar Relatório", width=140, fg_color=ACCENT_COLOR, hover_color=HOVER_COLOR, command=self.gerar_relatorio).pack(side="left")
        
        self.btn_exportar = ctk.CTkButton(linha2, text="📊 Salvar em Excel", width=140, fg_color=SUCCESS_COLOR, hover_color="#059669", state="disabled", command=self.exportar_excel)
        self.btn_exportar.pack(side="left", padx=10)
        
        self.caixa_relatorio = ctk.CTkTextbox(p, fg_color=CARD_COLOR, font=("Courier New", 14), border_width=1, border_color=BORDER_COLOR)
        self.caixa_relatorio.pack(fill="both", expand=True, pady=10)
        self.caixa_relatorio.insert("1.0", "Aguardando geração de relatório...\n\nPor favor, utilize os filtros acima e clique em 'Gerar Relatório'.")
        self.caixa_relatorio.configure(state="disabled")

    def gerar_relatorio(self):
        try:
            registros = self.buscar_notas_api(
                busca=self.rel_txt.get(),
                inicio=self.rel_ini.get(),
                fim=self.rel_fim.get(),
            )
        except Exception as e:
            self.show_toast(f"Erro ao gerar relatório pela API: {e}", "erro")
            self.btn_exportar.configure(state="disabled")
            return

        if self.rel_tipo.get() == "Apenas Vendas (Entradas)":
            registros = [r for r in registros if r["tipo"] == "Entrada"]
        elif self.rel_tipo.get() == "Apenas Despesas (Saídas)":
            registros = [r for r in registros if r["tipo"] == "Saída"]
        
        if not registros:
            self.show_toast("Nenhum dado encontrado para esses filtros.", "erro")
            self.btn_exportar.configure(state="disabled")
            return
            
        self.dados_relatorio = registros
        self.btn_exportar.configure(state="normal")
            
        vendas = 0.0; fornecedores = 0.0; operacionais = 0.0
        for r in registros:
            if r["tipo"] == "Entrada": vendas += r["valor"]
            elif r["tipo"] == "Saída" and "Estoque" in r["categoria"]: fornecedores += r["valor"]
            elif r["tipo"] == "Saída": operacionais += r["valor"]
            
        lucro_bruto = vendas - fornecedores
        lucro_liquido = vendas - fornecedores - operacionais
        margem_lucro = (lucro_liquido / vendas * 100) if vendas > 0 else 0
        
        texto =  "==========================================================\n"
        texto += "              RELATÓRIO GERENCIAL - PAPELARIA             \n"
        texto += "==========================================================\n\n"
        texto += f"Filtro Aplicado: {self.rel_tipo.get()}\n"
        texto += f"Termo Buscado: {self.rel_txt.get() if self.rel_txt.get() else 'Todos'}\n"
        texto += f"Período: {self.rel_ini.get() or 'Início'} a {self.rel_fim.get() or 'Hoje'}\n"
        texto += f"Total de Transações Detalhadas: {len(registros)}\n\n"
        
        if self.rel_tipo.get() != "Apenas Despesas (Saídas)":
            texto += "[+] RECEITAS\n"
            texto += f"    Vendas Totais: R$ {vendas:,.2f}\n\n"
            
        if self.rel_tipo.get() != "Apenas Vendas (Entradas)":
            texto += "[-] CUSTOS DIRETOS\n"
            texto += f"    Compras de Estoque (Fornecedores): R$ {fornecedores:,.2f}\n"
            texto += f"    LUCRO BRUTO: R$ {lucro_bruto:,.2f}\n\n"
            texto += "[-] CUSTOS INDIRETOS E DESPESAS FIXAS\n"
            texto += f"    Aluguel, Folha, Impostos, Luz, etc: R$ {operacionais:,.2f}\n\n"
            
        if self.rel_tipo.get() == "Todos os Registros":
            texto += "==========================================================\n"
            texto += f" RESULTADO LÍQUIDO DO PERÍODO: R$ {lucro_liquido:,.2f}\n"
            texto += f" MARGEM DE LUCRO LÍQUIDO: {margem_lucro:.2f}%\n"
            texto += "==========================================================\n"
        
        self.caixa_relatorio.configure(state="normal")
        self.caixa_relatorio.delete("1.0", "end")
        self.caixa_relatorio.insert("1.0", texto)
        self.caixa_relatorio.configure(state="disabled")
        self.show_toast("Relatório processado na tela!", "sucesso")

    def exportar_excel(self):
        if not self.dados_relatorio: return
        filepath = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Planilha Excel", "*.xlsx")], title="Salvar Relatório Como")
        
        if filepath:
            try:
                df = pd.DataFrame(self.dados_relatorio)
                df = df.rename(columns={
                    "data": "Data",
                    "tipo": "Tipo",
                    "categoria": "Categoria",
                    "descricao": "Descrição",
                    "estabelecimento": "Cliente/Fornecedor",
                    "valor": "Valor",
                })
                df = df[['Data', 'Tipo', 'Categoria', 'Descrição', 'Cliente/Fornecedor', 'Valor']]
                df.to_excel(filepath, index=False)
                self.show_toast("Arquivo Excel gerado com sucesso!", "sucesso")
            except Exception as e:
                self.show_toast("Erro. O arquivo Excel pode estar aberto.", "erro")

if __name__ == "__main__":
    app = NfeSystem()
    app.mainloop()
