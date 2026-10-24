# Arquitetura do Repositório

O `api-recommendation` é organizado por domínio, e não por camada técnica: cada feed
(`professionals`, `offers`, `suppliers`) é um pacote em `app/feeds/` com tudo o que precisa (rota,
serviço, estratégias de ranking, modelos de resposta e as consultas em arquivos `.cypher` e
`.cypher`). O que é comum a todos os feeds (configuração, autenticação, conexão, tratamento de
erros e utilitários de ranking) fica na raiz de `app/`. O serviço é somente leitura e tem uma única
fonte: o Neo4j `feeddb`, uma projeção descartável construída pelo job `database-bootstrap`.

<p>
  <a href="https://github.com/syvixor/skills-icons">
    <img src="https://skills.syvixor.com/api/icons?i=python,fastapi,neo4j,docker" height="48" alt="Arquitetura">
  </a>
</p>

- **Um pacote por feed**, `app/feeds/<feed>/` tem `router.py` (rota autenticada e rota pública),
  `service.py` (lê o grafo e aplica a estratégia), `strategies.py` (ranking puro, sem I/O),
  `schemas.py` (modelos de resposta) e `candidates.cypher`. Adicionar um feed é
  adicionar um pacote e registrar os dois routers em `app/main.py`.
- **Grafo como única fonte**, quando o Neo4j não está configurado, está fora do ar ou não tem
  snapshot ativo (`GraphUnavailableError`), o handler de `app/main.py` responde `503` com o código
  `FEED_UNAVAILABLE`. Erros de domínio (contexto inexistente, dado insuficiente) viram `404` ou
  `422`.
- **Neo4j tolerante**, `GraphService` (`app/database.py`) nunca derruba a aplicação: sem
  `DB_NEO4J_URI` ele fica desligado, e uma falha de conexão abre um período de espera
  (`GRAPH_RETRY_AFTER_SECONDS`) em que as requisições respondem `503` direto, sem pagar o timeout
  de novo.
- **Somente o snapshot ativo**, as consultas Cypher leem apenas nós com `source = "api-core"` e
  `sync_version` igual ao `SyncState.active_version`, então uma reconstrução em andamento nunca
  aparece pela metade. Esse formato é o contrato com o `database-bootstrap`.
- **Feeds públicos sanitizados**, `/public/feeds/*` usam modelos próprios, só com campos que podem
  ser expostos a anônimos, e usam a estratégia padrão de cada feed sobre o grafo. As respostas carregam
  `Cache-Control: public, max-age=…, stale-if-error=…`.
- **Autenticação por uma única chave**, `X-Recommendation-Key` (`app/security.py`), comparada com
  `hmac.compare_digest`. Em produção, `Settings.validate_runtime_security()` exige a chave com 32 a
  512 caracteres e Swagger desligado. O Neo4j do cluster é acessado
  por `bolt://` interno, sem TLS.
- **Segurança do container**, o `Dockerfile` usa `python:3.14-slim`, usuário não-root e instala as
  dependências com `--require-hashes` a partir do `requirements.lock`.

```Tree do Repositório
├── .github/
│   └── workflows/
├── app/
│   ├── feeds/
│   │   ├── professionals/        # router, service, strategies, schemas, candidates.cypher
│   │   ├── offers/               # idem
│   │   ├── suppliers/            # idem
│   │   ├── active_version.cypher # snapshot ativo (versão e idade)
│   │   ├── local_unit.cypher     # contexto geográfico
│   │   ├── common.py             # respostas, ranking, haversine
│   │   └── graph.py              # leitura do snapshot ativo
│   ├── config.py                 # Configurações (variáveis de ambiente)
│   ├── database.py               # GraphService
│   ├── dependencies.py           # Injeção do serviço do grafo
│   ├── errors.py
│   ├── health.py                 # /health/live e /health/ready
│   ├── main.py                   # Ponto de entrada (lifespan, routers, tratamento de erros)
│   ├── queries.py                # Leitura dos arquivos .cypher
│   └── security.py
├── http/                         # Coleção Bruno
├── tests/
│   ├── unit/
│   └── integration/              # Neo4j real (opt-in)
├── Dockerfile
├── pyproject.toml                # Configuração de ruff, coverage e mypy
├── pytest.ini
├── requirements.txt
├── requirements.dev.txt
├── requirements.lock
├── requirements-ci.lock
└── sonar-project.properties
```
