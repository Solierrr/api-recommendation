# api-recommendation

O `api-recommendation` é o motor de recomendação B2B da plataforma: recebe o nome de um serviço
técnico e devolve os profissionais mais qualificados para executá-lo, com pontuação e justificativa
para cada candidato. Os dados de profissionais, serviços e qualificações ficam modelados como um
grafo no Neo4j, o que permite consultas de ranqueamento que combinam afiliação, qualificações e
histórico de eventos (visualizações, cliques e contratações) de forma muito mais natural do que em
um modelo relacional. O serviço não é dono desses dados: ele os sincroniza periodicamente a partir
do PostgreSQL somente leitura do `api-core`, projetando o snapshot relacional em um grafo otimizado
para consultas de ranqueamento.

<p>

[![License](https://img.shields.io/github/license/Solierrr/api-recommendation)](https://github.com/Solierrr/api-recommendation/blob/main/LICENSE)
[![GitHub Last Commit](https://img.shields.io/github/last-commit/Solierrr/api-recommendation)](https://github.com/Solierrr/api-recommendation/commits)
[![GitHub Issues](https://img.shields.io/github/issues/Solierrr/api-recommendation)](https://github.com/Solierrr/api-recommendation/issues)
[![GitHub Pull Requests](https://img.shields.io/github/issues-pr/Solierrr/api-recommendation)](https://github.com/Solierrr/api-recommendation/pulls)
[![GitHub Contributors](https://img.shields.io/github/contributors/Solierrr/api-recommendation)](https://github.com/Solierrr/api-recommendation/graphs/contributors)
[![Release](https://img.shields.io/github/v/release/Solierrr/api-recommendation)](https://github.com/Solierrr/api-recommendation/releases)

</p>

<div align="center">

<p>
  <a href="https://github.com/syvixor/skills-icons">
    <img src="https://skills.syvixor.com/api/icons?i=python,fastapi,pydantic,neo4j,postgresql,docker" height="48" alt="Stack do Projeto">
  </a>
</p>

<p>

[![Python](https://img.shields.io/badge/Python_3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Pydantic](https://img.shields.io/badge/Pydantic-E92063?logo=pydantic&logoColor=white)](https://docs.pydantic.dev/)
[![Neo4j](https://img.shields.io/badge/Neo4j-008CC1?logo=neo4j&logoColor=white)](https://neo4j.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)

</p>

</div>

- **Recomendação de profissionais**, dado o nome de um serviço técnico, o motor consulta o grafo
  Neo4j e retorna os candidatos ranqueados por um conjunto de pesos (qualificação, afiliação,
  histórico de eventos) definidos em `app/core/weights.py`.
- **Telemetria de eventos**, cada interação relevante (visualização, clique, contratação) de um
  candidato recomendado é registrada via `POST /events`, alimentando o ranqueamento futuro.
- **Sincronização com o api-core**, o serviço mantém uma conexão somente leitura com o PostgreSQL
  do `api-core` e projeta esse estado no grafo Neo4j periodicamente (`SYNC_ON_STARTUP`) ou sob
  demanda via rota interna autenticada (`POST /internal/sync/core`).
- **Autenticação por API key**, todas as rotas de negócio exigem uma chave própria (`API_KEY`,
  `RECOMMENDATION_API_KEY` ou `SYNC_API_KEY`, conforme a rota), comparadas com `hmac.compare_digest`
  para evitar ataques de timing.

## Aprofunde-se no Projeto!

- [ARCHITECTURE.md](./ARCHITECTURE.md)
- [RUNNING.md](./RUNNING.md)
- {link do arquivo de deployment}

## Contribuindo

- [CONTRIBUTING.md](./CONTRIBUTING.md), convenções de commit, branch e Pull Request.
- [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md), código de conduta do projeto.
- [SECURITY.md](./SECURITY.md), como reportar vulnerabilidades de segurança.
