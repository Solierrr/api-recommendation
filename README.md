# api-recommendation

O `api-recommendation` é o motor de feeds da plataforma: recomenda profissionais, ofertas de placas
solares e fornecedores para as três telas de feed do marketplace. O ranking vem de um grafo no
Neo4j (`feeddb`), que é uma projeção descartável do PostgreSQL do `api-core`, reconstruída pelo
job [`database-bootstrap`](https://github.com/Solierrr/database-bootstrap). Este serviço só lê o
grafo: ele não sincroniza, não escreve e não depende do Neo4j para funcionar. Quando o grafo está
indisponível, ou não está configurado (como no QA), ele responde com uma amostra dos itens
elegíveis lida direto do PostgreSQL.

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

- **Três feeds**, `GET /feeds/professionals`, `GET /feeds/offers` e `GET /feeds/suppliers` devolvem
  os itens ranqueados por uma estratégia (`strategy`) e aceitam `company_id` e, quando faz sentido,
  `profession_id` ou `local_unit_id`. Exigem o header `X-Recommendation-Key` e são pensados para
  chamada servidor-a-servidor pelo `api-core`; a chave não pode ir para o navegador.
- **Feeds públicos**, `GET /public/feeds/{professionals|offers|suppliers}` não exigem chave, nunca
  tocam o Neo4j e respondem com `Cache-Control: public` (e `stale-if-error`) para que a Cloudflare
  atenda os anônimos sem chegar à origem.
- **Fallback SQL**, quando o grafo está fora do ar, sem snapshot ou não configurado, os feeds
  autenticados respondem com `source: "fallback"` em vez de erro: uma amostra aleatória entre os
  melhores itens elegíveis lidos do PostgreSQL, sem aplicar a estratégia pedida.
- **Somente leitura**, o serviço não escreve no Neo4j nem no PostgreSQL. O grafo é construído pelo
  `database-bootstrap`, e o contrato entre os dois está documentado na spec do projeto.
- **Saúde sem reinício em cascata**, `/health/live` não depende de nada e `/health/ready` só falha
  quando o PostgreSQL cai; o grafo aparece como `ready`, `unavailable`, `no_snapshot` ou `disabled`.

## Aprofunde-se no Projeto!

- [ARCHITECTURE.md](./ARCHITECTURE.md)
- [RUNNING.md](./RUNNING.md)

## Contribuindo

- [CONTRIBUTING.md](./CONTRIBUTING.md), convenções de commit, branch e Pull Request.
- [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md), código de conduta do projeto.
- [SECURITY.md](./SECURITY.md), como reportar vulnerabilidades de segurança.
