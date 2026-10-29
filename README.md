# api-recommendation

O `api-recommendation` é o motor de feeds da plataforma: recomenda profissionais, ofertas de placas
solares e fornecedores para as três telas de feed do marketplace. O ranking vem de um grafo no
Neo4j (`feeddb`), que é uma projeção descartável construída pelo job
[`database-bootstrap`](https://github.com/Solierrr/database-bootstrap). Este serviço só lê o grafo:
ele não sincroniza, não escreve e não fala com nenhum outro banco. Quando o grafo está indisponível,
sem snapshot ativo ou não configurado, as rotas de feed respondem `503` com o código
`FEED_UNAVAILABLE`.

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
    <img src="https://skills.syvixor.com/api/icons?i=python,fastapi,pydantic,neo4j,docker" height="48" alt="Stack do Projeto">
  </a>
</p>

<p>

[![Python](https://img.shields.io/badge/Python_3.14-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Pydantic](https://img.shields.io/badge/Pydantic-E92063?logo=pydantic&logoColor=white)](https://docs.pydantic.dev/)
[![Neo4j](https://img.shields.io/badge/Neo4j-008CC1?logo=neo4j&logoColor=white)](https://neo4j.com/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)

</p>

</div>

- **Três feeds**, `GET /feeds/professionals`, `GET /feeds/offers` e `GET /feeds/suppliers` devolvem
  os itens ranqueados por uma estratégia (`strategy`) e aceitam `company_id` e, quando faz sentido,
  `profession_id` ou `local_unit_id`. Exigem o header `X-Recommendation-Key` e são pensados para
  chamada servidor-a-servidor pelo `api-core`; a chave não pode ir para o navegador.
- **Feeds públicos**, `GET /public/feeds/{professionals|offers|suppliers}` não exigem chave, leem o
  grafo com a estratégia padrão de cada feed e respondem com `Cache-Control: public` (e
  `stale-if-error`) para que a Cloudflare atenda os anônimos sem chegar à origem.
  O navegador só os lê a partir das origens de `CORS_ALLOWED_ORIGINS` (lista separada por vírgula,
  sem credenciais e sem `*`); o header `X-Recommendation-Key` não é aceito em chamadas CORS. Com a
  Cloudflare na frente, use uma única origem por ambiente ou inclua `Origin` na chave de cache.
- **Sem caminho alternativo**, quando o grafo está fora do ar, sem snapshot ou não configurado, todas as rotas
  de feed respondem `503` com `FEED_UNAVAILABLE`.
- **Somente leitura**, o serviço não escreve no Neo4j. O grafo é construído pelo
  `database-bootstrap`, e o contrato entre os dois está documentado na spec do projeto.
- **Saúde sem reinício em cascata**, `/health/live` não depende de nada e `/health/ready` sempre
  responde `200`; o grafo aparece como `ready`, `unavailable`, `no_snapshot` ou `disabled`.

## Aprofunde-se no Projeto!

- [ARCHITECTURE.md](./ARCHITECTURE.md)
- [RUNNING.md](./RUNNING.md)

## Contribuindo

- [CONTRIBUTING.md](./CONTRIBUTING.md), convenções de commit, branch e Pull Request.
- [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md), código de conduta do projeto.
- [SECURITY.md](./SECURITY.md), como reportar vulnerabilidades de segurança.
