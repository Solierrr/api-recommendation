# Rodando o Projeto Localmente

Este repositório é Python. O processo local é: clonar, criar um ambiente virtual, instalar as
dependências (via `requirements.txt`/`requirements.dev.txt`, ou os lockfiles com hashes travados
para reproduzir exatamente o ambiente de CI) e subir a aplicação via `uvicorn`. O serviço só
precisa do PostgreSQL do `api-core`; o Neo4j é opcional, porque sem ele os feeds usam o fallback SQL.

<p>
  <a href="https://github.com/syvixor/skills-icons">
    <img src="https://skills.syvixor.com/api/icons?i=python,fastapi,pydantic,neo4j,postgresql" height="48" alt="Rodando o Projeto — Python">
  </a>
</p>

## Possíveis Impedimentos

- **Python 3.14 instalado localmente**, a mesma versão usada no `Dockerfile` (`python:3.14-slim`)
  — rodar fora do container exige essa versão instalada na máquina.
- **Acesso ao PostgreSQL do `api-core`**, obrigatório: o serviço não sobe sem ele
  (`DB_POSTGRES_HOST`, `DB_POSTGRES_PORT`, `DB_POSTGRES_CORE`, `DB_POSTGRES_USER`,
  `DB_POSTGRES_PASSWORD`). O schema real é o do `database-console/db/core`.
- **Neo4j `feeddb`, opcional**, preencha `DB_NEO4J_URI`, `DB_NEO4J_USER`, `DB_NEO4J_PASSWORD` e
  `DB_NEO4J_FEED` para ranquear pelo grafo. O grafo é populado pelo job
  [`database-bootstrap`](https://github.com/Solierrr/database-bootstrap); sem ele (ou sem as
  variáveis), os feeds respondem com `source: "fallback"`.
- **Chave de recomendação**, `RECOMMENDATION_API_KEY` protege `/feeds/*`. Fora de produção, sem a
  variável, as rotas ficam abertas; em produção ela é obrigatória.

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
`pip install -e .`. `requirements.txt` traz só o runtime, `requirements.dev.txt` acrescenta
lint/testes/auditoria, e `requirements.lock`/`requirements-ci.lock` são lockfiles com hashes (o
mesmo lockfile instalado com `--require-hashes` dentro do `Dockerfile`).

```Comandos para instalação de dependências (desenvolvimento)
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt -r requirements.dev.txt
```

```Comandos para instalação de dependências (reproduzindo o CI, com hashes travados)
python -m venv .venv
.venv\Scripts\activate
pip install --require-hashes -r requirements-ci.lock
```

Copie o `.env.example` para `.env` e preencha, no mínimo, as variáveis `DB_POSTGRES_*`. Para gerar a
chave de recomendação localmente:

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
ruff check app tests
ruff format --check app tests
mypy app
```

Os testes de integração rodam contra bancos reais descartáveis e só executam com a confirmação
explícita `INTEGRATION_ALLOW_DESTRUCTIVE=true`, porque truncam as tabelas do `coredb` e apagam todo
o grafo:

```Comandos para subir os bancos de teste
docker run -d --name rec-neo4j -p 127.0.0.1:7687:7687 \
  -e NEO4J_AUTH=neo4j/test-password-for-ci \
  -e NEO4J_initial_dbms_default__database=feeddb neo4j:5.26-community
docker run -d --name rec-postgres -p 127.0.0.1:5432:5432 \
  -e POSTGRES_PASSWORD=test-password-for-ci -e POSTGRES_DB=coredb postgres:16
```

Carregue o schema do `api-core` com `enums.sql`, `schema.sql` e a migração
`V10__technician_review_status.sql` do `database-console/db/core` (por exemplo com `psql -f`) e rode:

```Comando dos testes de integração
INTEGRATION_ALLOW_DESTRUCTIVE=true \
NEO4J_INTEGRATION_URI=bolt://127.0.0.1:7687 NEO4J_INTEGRATION_PASSWORD=test-password-for-ci \
POSTGRES_INTEGRATION_HOST=127.0.0.1 POSTGRES_INTEGRATION_PASSWORD=test-password-for-ci \
pytest
```

Nunca aponte essas variáveis para os bancos reais.

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
