# api-recommendation

Motor de Recomendação B2B: recebe o nome de um serviço e devolve os profissionais mais
qualificados para executá-lo, com pontuação e justificativa. Os dados (profissionais, serviços,
qualificações) ficam modelados como um grafo no Neo4j.

## Stack

- **Python 3.12** + **FastAPI** (API HTTP assíncrona)
- **Neo4j** (banco de dados de grafos, via driver assíncrono oficial)
- **Pydantic** (validação de entrada/saída)
- **pytest** (testes) + **ruff** (lint) + **SonarQube** (qualidade de código)
- **Docker** (containerização)

## Como rodar localmente

1. Crie um ambiente virtual e instale as dependências:

   ```bash
   python -m venv .venv
   .venv\Scripts\activate   # Windows
   pip install -r requirements-dev.txt
   ```

2. Copie `.env.example` para `.env` e preencha com as credenciais da sua instância Neo4j
   (ex: AuraDB) e gere uma API key:

   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

3. (Opcional) Popule o banco com uma massa de dados de teste:

   ```bash
   python scripts/seed.py
   ```

   **Atenção:** este script apaga todos os dados existentes no banco configurado antes de
   recriar a massa de teste. Use apenas em bancos de desenvolvimento.

4. Suba a API:

   ```bash
   uvicorn app.main:app --reload
   ```

5. Acesse a documentação interativa (Swagger) em `http://localhost:8000/docs`.

## Como rodar com Docker

```bash
docker build -t api-recommendation .
docker run --rm -p 8000:8000 --env-file .env api-recommendation
```

## Endpoints

| Método | Rota              | Autenticação    | Descrição                                          |
|--------|--------------------|-----------------|-----------------------------------------------------|
| GET    | `/health`          | Nenhuma         | Healthcheck: verifica a conexão com o Neo4j.        |
| POST   | `/recommendations` | `X-API-Key`     | Retorna os candidatos ranqueados para um serviço.   |
| POST   | `/events`          | `X-API-Key`     | Registra um evento de telemetria (VIEW/CLICK/HIRE). |

### Autenticação

As rotas `/recommendations` e `/events` exigem o header `X-API-Key` com o valor configurado em
`API_KEY` no `.env`. Requisições sem a chave ou com uma chave inválida recebem `401 Unauthorized`.
`/health` é intencionalmente público, para não travar healthchecks de infraestrutura
(load balancers, orquestradores) que normalmente não enviam credenciais.

### Exemplo: `POST /recommendations`

```bash
curl -X POST http://localhost:8000/recommendations \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <sua-api-key>" \
  -d '{"service_name": "Desenvolvimento Python", "min_level": 2, "limit": 5}'
```

### Exemplo: `POST /events`

```bash
curl -X POST http://localhost:8000/events \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <sua-api-key>" \
  -d '{"user_id": "empresa_123", "candidate_id": "prof_1", "event_type": "HIRE"}'
```

## Testes e qualidade

```bash
pytest --cov=app --cov-report=term-missing   # testes unitários + cobertura
ruff check app tests scripts                 # lint
```

O pipeline de CI (`.github/workflows/ci.yml`) roda os testes e gera o relatório de cobertura a
cada push/PR; `quality.yml` roda o lint; `sonarqube.yml` envia os resultados para o SonarQube.

## Estrutura do projeto

```
app/
  api/            # Rotas HTTP (FastAPI routers)
  core/           # Regras de negócio (services)
  repositories/   # Acesso ao Neo4j (queries Cypher)
  schemas/        # Modelos Pydantic de entrada/saída
  config.py       # Configurações (variáveis de ambiente)
  database.py     # Gerenciamento da conexão com o Neo4j
  main.py         # Ponto de entrada da aplicação
scripts/
  seed.cypher     # Massa de dados de teste
  seed.py         # Executa o seed.cypher contra o banco configurado
tests/            # Testes unitários (pytest)
```

## Convenções

**Commits** seguem o padrão: `fix:`, `feat:`, `docs:`, `style:`, `refactor:`, `build:`, `test:`,
`chore:`, `ci:`.

**Branches** seguem o padrão: `feat/`, `fix/`, `docs/`, `style/`, `refactor/`, `build/`, `test/`,
`chore/`, `ci/`, `hotfix/`, `release/`.
