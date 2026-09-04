# Rodando o Projeto Localmente

Este repositório é Python. O processo local é: clonar, criar um ambiente virtual, instalar as
dependências (via `requirements.txt`/`requirements-dev.txt`, ou os lockfiles com hashes travados
para reproduzir exatamente o ambiente de CI) e subir a aplicação via `uvicorn`. Antes de iniciar,
verifique a seção de impedimentos abaixo — o serviço depende de duas fontes de dados externas
(Neo4j e PostgreSQL) mesmo em ambiente local.

<p>
  <a href="https://github.com/syvixor/skills-icons">
    <img src="https://skills.syvixor.com/api/icons?i=python,fastapi,pydantic,neo4j,postgresql" height="48" alt="Rodando o Projeto — Python">
  </a>
</p>

## Possíveis Impedimentos

- **Python 3.12 instalado localmente**, a mesma versão usada no `Dockerfile` (`python:3.12-slim`)
  — rodar fora do container exige essa versão instalada na máquina.
- **Acesso a uma instância Neo4j**, o serviço se conecta a um banco de grafos via driver
  assíncrono oficial (`NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`) — use uma instância local
  (Docker) ou uma instância gerenciada (ex: AuraDB) e preencha as credenciais no `.env`.
- **Acesso ao PostgreSQL do `api-core`**, a sincronização de dados (`SyncService`) lê o banco
  relacional do `api-core` em modo somente leitura (`DB_POSTGRES_HOST`, `DB_POSTGRES_PORT`,
  `DB_POSTGRES_CORE`, `DB_POSTGRES_USER`, `DB_POSTGRES_PASSWORD`) — sem essas credenciais, a API
  sobe mas a sincronização e as rotas que dependem de dados sincronizados falham.
- **API keys locais**, `API_KEY`, `RECOMMENDATION_API_KEY` e `SYNC_API_KEY` precisam ser geradas
  manualmente para autenticar as rotas de negócio localmente (ver comando abaixo) — sem elas, as
  rotas protegidas retornam `503` ou `401`.

## Instalação do Projeto

### Iniciando o repositório com o Github

<p>
  <a href="https://github.com/syvixor/skills-icons">
    <img src="https://skills.syvixor.com/api/icons?i=github,vscode" height="48" alt="Frameworks">
  </a>
</p>

Clone o repositório e abra no VS Code.

```Comandos para clonar o repositório
git clone https://github.com/Solierrr/api-recommendation.git
cd ./api-recommendation
code . -r
```

### Instalando dependências necessárias para rodar o projeto localmente

<p>
  <a href="https://github.com/syvixor/skills-icons">
    <img src="https://skills.syvixor.com/api/icons?i=python" height="48" alt="Frameworks">
  </a>
</p>

Crie um ambiente virtual antes de instalar as dependências, para não poluir o Python global da
máquina. O `pyproject.toml` deste repositório configura só as ferramentas de qualidade (`ruff`,
`coverage`, `mypy`) — não há `[project]`/`[build-system]`, então o pacote não é instalável via
`pip install -e .`. As dependências ficam em arquivos `requirements*` separados:
`requirements.txt` traz só o runtime, `requirements-dev.txt` acrescenta lint/testes/auditoria, e
`requirements.lock`/`requirements-ci.lock` são lockfiles gerados via `uv pip compile
--generate-hashes` (o mesmo lockfile instalado com `--require-hashes` dentro do `Dockerfile`) — use
os lockfiles quando quiser reproduzir exatamente o ambiente de CI/produção, ou os arquivos soltos
para desenvolvimento do dia a dia.

```Comandos para instalação de dependências (desenvolvimento)
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
```

```Comandos para instalação de dependências (reproduzindo o CI, com hashes travados)
python -m venv .venv
.venv\Scripts\activate
pip install --require-hashes -r requirements-ci.lock
```

Copie um `.env.example` (se existir) ou crie um `.env` na raiz com, no mínimo, as variáveis de
`NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, `DB_POSTGRES_HOST`/`DB_POSTGRES_PORT`/
`DB_POSTGRES_CORE`/`DB_POSTGRES_USER`/`DB_POSTGRES_PASSWORD` e as três API keys (`API_KEY`,
`RECOMMENDATION_API_KEY`, `SYNC_API_KEY`). Para gerar uma API key localmente:

```Comando para gerar uma API key local
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Suba a aplicação:

```Comando de start
uvicorn app.main:app --reload
```

Acesse a documentação interativa (Swagger) em `http://localhost:8000/docs` — disponível apenas
quando `DOCS_ENABLED=true`, o padrão em desenvolvimento; em produção essa variável é forçada a
`false` por `Settings.validate_runtime_security()`.

### Rodando testes e lint

<p>
  <a href="https://github.com/syvixor/skills-icons">
    <img src="https://skills.syvixor.com/api/icons?i=pytest,ruff" height="48" alt="Qualidade">
  </a>
</p>

```Comandos de testes e lint
pytest --cov=app --cov-report=term-missing
ruff check app tests scripts
```

### Rodando com Docker

<p>
  <a href="https://github.com/syvixor/skills-icons">
    <img src="https://skills.syvixor.com/api/icons?i=docker" height="48" alt="Docker">
  </a>
</p>

```Comandos para build e run via Docker
docker build -t api-recommendation .
docker run --rm -p 8000:8000 --env-file .env api-recommendation
```
