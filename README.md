# Controle Fiscal TechStore - Sistema de NF-e e Livro Caixa

Este projeto é a materialização do Documento de Visão de um sistema desktop para controle fiscal, desenvolvido para auxiliar pequenos comércios na gestão de suas compras, vendas e despesas.

## 👥 Equipe
* Otton Simão Gouveia Cavalcante
* Pablo Dias dos Santos Soares
* Raul Moreira de Queiroz
* Roberto Qiming Li
* Samuel Rodrigues da Silva


## 🛠️ Tecnologias Utilizadas
* **Python 3**: linguagem principal do projeto.
* **Tkinter**: base nativa da interface desktop.
* **CustomTkinter**: componentes visuais modernos para o aplicativo desktop.
* **Flask**: API HTTP usada para testes, integração e validação via Postman.
* **SQLite3**: banco de dados local usado para usuários e notas fiscais.
* **Pandas**: tratamento de dados para exportação de relatórios.
* **OpenPyXL**: geração de arquivos Excel `.xlsx`.
* **Pytest**: testes automatizados de sistema, API e E2E.
* **Pytest HTML**: geração dos relatórios HTML das rodadas de teste.

## 🚀 Como executar o projeto
1. Crie e ative um ambiente virtual, se necessário: `python -m venv .venv`
2. Instale as dependências: `pip install -r requirements.txt`
3. Execute o sistema desktop: `python app.py`
4. Ao iniciar pelo `app.py`, o banco SQLite é inicializado e a API Flask sobe automaticamente em segundo plano.
5. Para executar somente a API Flask, sem abrir a interface: `python -m backend.api`
6. Opcionalmente, inicialize o banco manualmente: `python -m backend.database`

Credenciais padrão:
* **Administrador:** `admin` / `admin`
* **Gerente:** `gerente` / `123`
* **Operador:** `caixa` / `123`

## 🌐 API Flask
A API sobe localmente em:

`http://127.0.0.1:5000`

Endpoints disponíveis:
* `GET /api/health`: verifica se a API está online.
* `POST /api/login`: autentica usuário.
* `GET /api/notas`: lista notas fiscais cadastradas.
* `GET /api/notas?busca=Venda`: lista notas filtrando por texto.
* `POST /api/notas`: cadastra uma nova nota.
* `GET /api/resumo`: retorna entradas, saídas e saldo.


## 📁 Estrutura do projeto
* `app.py`: ponto de entrada do aplicativo desktop.
* `frontend/interface.py`: interface desktop em CustomTkinter.
* `backend/api.py`: API Flask usada para testes e integração.
* `backend/database.py`: criação, migração simples e carga inicial do banco SQLite.
* `backend/services.py`: regras de negócio compartilhadas entre interface e API.
* `testes/`: testes de sistema e relatório HTML dos testes.

