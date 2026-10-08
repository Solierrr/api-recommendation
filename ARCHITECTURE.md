# Arquitetura do Repositório

O `api-recommendation` é organizado por domínio, e não por camada técnica: cada feed
(`professionals`, `offers`, `suppliers`) é um pacote em `app/feeds/` com tudo o que precisa (rota,
serviço, estratégias de ranking, modelos de resposta e as consultas em arquivos `.cypher` e
`.sql`). O que é comum a todos os feeds (configuração, autenticação, conexões, tratamento de erros
e utilitários de ranking) fica na raiz de `app/`. O serviço é somente leitura e tem duas fontes:
o Neo4j `feeddb`, uma projeção descartável do `api-core` construída pelo job `database-bootstrap`,
e o PostgreSQL do `api-core`, usado como rede de segurança quando o grafo não responde.

<p>
  <a href="https://github.com/syvixor/skills-icons">
    <img src="https://skills.syvixor.com/api/icons?i=python,fastapi,neo4j,postgresql,docker" height="48" alt="Arquitetura">
  </a>
</p>

- **Um pacote por feed**, `app/feeds/<feed>/` tem `router.py` (rota autenticada e rota pública),
  `service.py` (decide entre o grafo e o fallback), `strategies.py` (ranking puro, sem I/O),
  `schemas.py` (modelos de resposta), `candidates.cypher` e `fallback.sql`. Adicionar um feed é
  adicionar um pacote e registrar os dois routers em `app/main.py`.
- **Grafo primeiro, SQL como rede de segurança**, cada serviço tenta o grafo e, se o Neo4j não está
  configurado, está fora do ar ou não tem snapshot ativo (`GraphUnavailableError`), cai no
  `fallback.sql` e devolve `source: "fallback"` com um aviso. Erros de domínio (contexto inexistente,
  dado insuficiente) nunca disparam o fallback: viram `404` ou `422`. Se nem o PostgreSQL responde,
  a resposta é `503` com o código `FEED_UNAVAILABLE`.
- **Neo4j tolerante**, `GraphService` (`app/database.py`) nunca derruba a aplicação: sem
  `DB_NEO4J_URI` ele fica desligado (é o caso do QA no Render, que sempre usa o fallback), e uma
  falha de conexão abre um período de espera (`GRAPH_RETRY_AFTER_SECONDS`) em que as requisições
  vão direto ao SQL, sem pagar o timeout de novo.
- **Somente o snapshot ativo**, as consultas Cypher leem apenas nós com `source = "api-core"` e
  `sync_version` igual ao `SyncState.active_version`, então uma reconstrução em andamento nunca
  aparece pela metade. Esse formato é o contrato com o `database-bootstrap`.
- **Fallback amostral**, cada `fallback.sql` seleciona os `FALLBACK_POOL_SIZE` melhores itens
  elegíveis e sorteia `RECOMMENDATION_RESULT_LIMIT` entre eles, para o feed rotacionar. A regra de
  elegibilidade (modelo aprovado, fornecedor ativo com assinatura paga, técnico aprovado de usuário
  ativo) é a mesma do grafo e fica documentada no contrato do `database-bootstrap`.
- **Feeds públicos sanitizados**, `/public/feeds/*` usam modelos próprios, só com campos que podem
  ser expostos a anônimos, e sempre são servidos pelo SQL. As respostas carregam
  `Cache-Control: public, max-age=…, stale-if-error=…`.
- **Autenticação por uma única chave**, `X-Recommendation-Key` (`app/security.py`), comparada com
  `hmac.compare_digest`. Em produção, `Settings.validate_runtime_security()` exige a chave com 32 a
  512 caracteres, `sslmode` seguro no PostgreSQL e Swagger desligado. O Neo4j do cluster é acessado
  por `bolt://` interno, sem TLS.
- **Segurança do container**, o `Dockerfile` usa `python:3.12-slim`, usuário não-root e instala as
  dependências com `--require-hashes` a partir do `requirements.lock`.

```Tree do Repositório
├── .github/
│   └── workflows/
├── app/
│   ├── feeds/
│   │   ├── professionals/        # router, service, strategies, schemas, candidates.cypher, fallback.sql
│   │   ├── offers/               # idem
│   │   ├── suppliers/            # idem
│   │   ├── active_version.cypher # snapshot ativo (versão e idade)
│   │   ├── local_unit.cypher     # contexto geográfico
│   │   ├── common.py             # respostas, ranking, haversine, orquestração grafo/fallback
│   │   ├── fallback.py           # execução do SQL e formatação dos itens do fallback
│   │   └── graph.py              # leitura do snapshot ativo
│   ├── config.py                 # Configurações (variáveis de ambiente)
│   ├── database.py               # PostgresService e GraphService
│   ├── dependencies.py           # Injeção dos serviços de banco
│   ├── errors.py
│   ├── health.py                 # /health/live e /health/ready
│   ├── main.py                   # Ponto de entrada (lifespan, routers, tratamento de erros)
│   ├── queries.py                # Leitura dos arquivos .cypher e .sql
│   └── security.py
├── http/                         # Coleção Bruno
├── tests/
│   ├── unit/
│   └── integration/              # Neo4j e PostgreSQL reais (opt-in)
├── Dockerfile
├── pyproject.toml                # Configuração de ruff, coverage e mypy
├── pytest.ini
├── requirements.txt
├── requirements-dev.txt
├── requirements.lock
├── requirements-ci.lock
└── sonar-project.properties
```
