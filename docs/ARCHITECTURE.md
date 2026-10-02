# Arquitetura do Repositório

O `api-recommendation` segue uma arquitetura em camadas dentro do pacote `app/`: rotas HTTP
(`api/`) delegam para serviços de regra de negócio (`core/`), que por sua vez consultam
repositórios (`repositories/`) responsáveis por toda a interação com Neo4j e PostgreSQL. Modelos
Pydantic (`schemas/`) validam entrada e saída em cada rota. Essa separação existe porque o serviço
combina duas fontes de dados com papéis muito distintos: o PostgreSQL do `api-core` é a fonte de
verdade, acessada em modo somente leitura, enquanto o Neo4j é uma projeção derivada, otimizada para
consultas de grafo de ranqueamento — a camada de repositório isola essa diferença do restante da
aplicação.

<p>
  <a href="https://github.com/syvixor/skills-icons">
    <img src="https://skills.syvixor.com/api/icons?i=python,fastapi,neo4j,postgresql,docker" height="48" alt="Arquitetura">
  </a>
</p>

- **Arquitetura em camadas (API → Core → Repositories)**, `app/api/` expõe os routers FastAPI e
  aplica a autenticação de cada rota; `app/core/` concentra as regras de negócio (ranqueamento,
  sincronização, eventos); `app/repositories/` isola as queries Cypher (Neo4j) e SQL (PostgreSQL),
  para que uma troca de banco não vaze para as camadas superiores.
- **Duas fontes de dados com responsabilidades diferentes**, o PostgreSQL (`app/database.py`,
  classe `PostgresService`) é acessado com um pool `asyncpg` restrito a transações
  `readonly=True`, já que o schema (`scripts/core_schema.sql`) pertence ao `api-core`; o Neo4j
  (classe `Neo4jService`) recebe leituras e escritas através de sessões dedicadas
  (`read_session`/`write_session`), mantendo o padrão CQRS mesmo dentro do mesmo banco.
- **Sincronização Postgres → Neo4j**, `app/core/sync_service.py` e
  `app/repositories/graph_sync_repository.py` implementam a projeção do snapshot relacional do
  `api-core` (ofertas, profissionais, profissões, qualificações, afiliações) para o grafo, disparada
  na subida da aplicação quando `SYNC_ON_STARTUP=true` ou sob demanda pela rota interna
  `POST /internal/sync/core`, protegida por lock de execução (`SyncInProgressError`) e por
  validações de segurança do snapshot (`UnsafeSnapshotError`, retenção mínima de domínio via
  `SYNC_MIN_DOMAIN_RETENTION_RATIO`).
- **Autenticação por API key com escopos distintos**, três chaves independentes controlam acesso:
  `API_KEY` (rotas legadas de recomendação), `RECOMMENDATION_API_KEY` (rotas novas de recomendação)
  e `SYNC_API_KEY` (rota interna de sincronização) — comparadas com `hmac.compare_digest` para
  mitigar ataques de timing (`app/core/security.py`, `app/api/sync.py`). Em produção,
  `Settings.validate_runtime_security()` (`app/config.py`) exige que as três chaves existam, tenham
  entre 32 e 512 caracteres e sejam diferentes entre si, além de forçar TLS no Neo4j
  (`neo4j+s://`/`bolt+s://`), `sslmode` seguro no Postgres e a desativação do Swagger/Redoc.
- **Segurança do container**, o `Dockerfile` usa `python:3.12-slim` como imagem base, cria um
  usuário e grupo de sistema não-root (`app`) e roda o processo `uvicorn` com esse usuário, nunca
  como root. As dependências são instaladas via `pip install --require-hashes` a partir do
  `requirements.lock`, um lockfile gerado com `uv pip compile --generate-hashes`, garantindo que
  cada pacote instalado corresponda exatamente ao hash travado e reduzindo o risco de dependências
  adulteradas na cadeia de suprimento.
- **Integração com o `api-core`**, este serviço não expõe escrita alguma sobre os dados do
  `api-core` — a conexão com o PostgreSQL compartilhado é somente leitura
  (`SET default_transaction_read_only = on`, transações `readonly=True`), e o schema consumido
  (`scripts/core_schema.sql`) é uma cópia de referência do schema real do `api-core`, usada para
  desenvolvimento e testes locais.

```Tree do Repositório
├── .github/
│   └── workflows/
│       ├── ci.yml              # Testes + cobertura
│       ├── quality.yml         # Lint (ruff)
│       ├── qa-sync.yml
│       ├── release.yml
│       ├── repo-cleanup.yml
│       └── sonarqube.yml       # Análise SonarQube
├── app/
│   ├── api/                    # Rotas HTTP (FastAPI routers)
│   │   ├── events.py
│   │   ├── health.py
│   │   ├── recommendations.py
│   │   └── sync.py
│   ├── core/                   # Regras de negócio (services)
│   │   ├── candidate_service.py
│   │   ├── errors.py
│   │   ├── event_service.py
│   │   ├── ranking_service.py
│   │   ├── recommendation_engine.py
│   │   ├── recommendation_service.py
│   │   ├── security.py
│   │   ├── sync_service.py
│   │   └── weights.py
│   ├── repositories/           # Acesso a Neo4j (Cypher) e PostgreSQL (SQL)
│   │   ├── candidate_repository.py
│   │   ├── core_candidate_repository.py
│   │   ├── core_graph_repository.py
│   │   ├── event_repository.py
│   │   ├── graph_sync_repository.py
│   │   └── recommendation_repository.py
│   ├── schemas/                 # Modelos Pydantic de entrada/saída
│   │   ├── event.py
│   │   ├── recommendation.py
│   │   ├── recommendations.py
│   │   └── responses.py
│   ├── config.py                # Configurações (variáveis de ambiente)
│   ├── database.py               # Gerenciamento das conexões Neo4j/PostgreSQL
│   └── main.py                   # Ponto de entrada da aplicação (lifespan, routers)
├── scripts/
│   ├── core_schema.sql          # Schema de referência do PostgreSQL do api-core
│   ├── seed.cypher               # Massa de dados de teste para o Neo4j
│   └── seed.py                   # Executa o seed.cypher contra o banco configurado
├── tests/                        # Testes unitários e de integração (pytest)
├── Dockerfile
├── README.md
├── ARCHITECTURE.md
├── RUNNING.md
├── pyproject.toml                # Configuração de ruff, coverage e mypy
├── pytest.ini
├── requirements.txt               # Dependências de runtime
├── requirements-dev.txt           # Dependências de desenvolvimento (lint, testes, auditoria)
├── requirements.lock              # Lockfile de runtime com hashes (uv)
├── requirements-ci.lock           # Lockfile de runtime + dev com hashes (uv)
└── sonar-project.properties
```
