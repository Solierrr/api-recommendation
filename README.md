<p align="center">
  <img src="./assets/readme/banners/fastapi.png" alt="FastAPI" width="100%">
</p>

<p align="center">
  <img src="./assets/readme/stacks/python.png" width="100" hspace="8" alt="Python" title="Python">
  <img src="./assets/readme/stacks/neo4j.png" width="100" hspace="8" alt="Neo4j" title="Neo4j">
  <img src="./assets/readme/stacks/postgresql.png" width="100" hspace="8" alt="PostgreSQL" title="PostgreSQL">
  <img src="./assets/readme/stacks/swagger.png" width="100" hspace="8" alt="Swagger" title="Swagger">
  <img src="./assets/readme/stacks/bruno.png" width="100" hspace="8" alt="Bruno" title="Bruno">
</p>

# Feeds de recomendações

[![License](https://img.shields.io/github/license/Solierrr/api-recommendation)](https://github.com/Solierrr/api-recommendation/blob/main/LICENSE)
[![GitHub Last Commit](https://img.shields.io/github/last-commit/Solierrr/api-recommendation)](https://github.com/Solierrr/api-recommendation/commits)
[![GitHub Pull Requests](https://img.shields.io/github/issues-pr/Solierrr/api-recommendation)](https://github.com/Solierrr/api-recommendation/pulls)
[![Release](https://img.shields.io/github/v/release/Solierrr/api-recommendation)](https://github.com/Solierrr/api-recommendation/releases)

Este serviço recomenda profissionais, ofertas de placas solares e fornecedores para apoiar a escolha de quem contrata e compra na plataforma. Cada lista apresenta motivos e métricas de ordenação. A pessoa pode comparar alternativas por avaliação, experiência, preço, eficiência ou proximidade, conforme o tipo de recomendação disponível.

As recomendações usam um retrato dos dados de negócio no Neo4j. Quando ele não está disponível, o serviço consulta uma amostra de itens elegíveis no PostgreSQL e informa essa origem. As listas públicas usam apenas essa alternativa. O serviço lê os dados e não altera o cadastro ou reconstrói o grafo.

## Aprofunde-se no Projeto!

- [OVERVIEW.md](./docs/OVERVIEW.md), finalidade e regras de produto.
- [ARCHITECTURE.md](./docs/ARCHITECTURE.md), componentes, dados e integrações.
- [RUNNING.md](./docs/RUNNING.md), preparação e execução local.
- [API.md](./docs/API.md), autenticação e uso do contrato.
- [FEEDS.md](./docs/FEEDS.md), detalhes do fluxo ou modelo de dados.
- [DEPLOY.md](./docs/DEPLOY.md), ambientes e publicação.
- [STATUS.md](./docs/STATUS.md), limites observados.
- [Dados](./database/), modelos e responsabilidades de persistência.
- [Fluxos](./flows/), etapas e casos de erro do repositório.
- [PENDENCIAS.md](./PENDENCIAS.md), questões para revisão.

## Contribuindo

- [CONTRIBUTING.md](https://github.com/Solierrr/.github/blob/main/.github/CONTRIBUTING.md), convenções de contribuição.
- [CODE_OF_CONDUCT.md](https://github.com/Solierrr/.github/blob/main/CODE_OF_CONDUCT.md), código de conduta.
- [SECURITY.md](https://github.com/Solierrr/.github/blob/main/SECURITY.md), relato de vulnerabilidades.
