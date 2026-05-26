# Controle Fiscal TechStore - Sistema de NF-e e Livro Caixa

Este projeto é a materialização do Documento de Visão de um sistema desktop para controle fiscal, desenvolvido para auxiliar pequenos comércios na gestão de suas compras, vendas e despesas.

## 👥 Equipe
* Otton Simão Gouveia Cavalcante
* Pablo Dias dos Santos Soares
* Raul Moreira de Queiroz
* Roberto Qiming Li
* Samuel Rodrigues da Silva


## 🛠️ Tecnologias Utilizadas

### Aplicação
* **Python 3**: linguagem principal do projeto.
* **Tkinter**: base nativa da interface desktop.
* **CustomTkinter**: componentes visuais modernos para o aplicativo desktop.
* **Flask**: microframework web usado para criar APIs HTTP e expor serviços do backend.
* **SQLite3**: banco de dados local usado para usuários e notas fiscais.
* **Pandas**: tratamento de dados para exportação de relatórios.
* **OpenPyXL**: geração de arquivos Excel `.xlsx`.

### Suíte de Testes
* **Pytest**: framework principal dos testes automatizados unitários, de API e E2E.
* **Flask test_client**: cliente de teste usado para validar endpoints da API sem depender de servidor externo.
* **Playwright**: automação dos testes E2E em navegador Chromium headless.
* **Pytest HTML**: geração do relatório HTML da execução dos testes.

## 🚀 Como executar o projeto
1. Crie e ative um ambiente virtual, se necessário: `python -m venv .venv`
2. Instale as dependências: `pip install -r requirements.txt`
3. Execute o sistema desktop: `python app.py`
4. Ao iniciar pelo `app.py`, o banco SQLite é inicializado e a API Flask sobe automaticamente em segundo plano.
5. A interface desktop consome a API local em `http://127.0.0.1:5000/api`.
6. Opcionalmente, inicialize apenas o banco manualmente: `python -m backend.database`

Credenciais padrão:
* **Administrador:** `admin` / `admin`
* **Gerente:** `gerente` / `123`
* **Operador:** `caixa` / `123`


## 📁 Estrutura do projeto
* `app.py`: ponto de entrada do sistema; inicializa o banco, sobe a API Flask em segundo plano e abre a interface.
* `frontend/interface.py`: interface desktop em CustomTkinter que consome a API HTTP local.
* `backend/api.py`: API Flask com endpoints de autenticação, notas e resumo financeiro.
* `backend/database.py`: criação, migração simples e carga inicial do banco SQLite.
* `backend/services.py`: regras de negócio e validações compartilhadas.
* `testes/`: testes de sistema e relatório HTML dos testes.
