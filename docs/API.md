<p align="center">
  <img src="../assets/readme/banners/fastapi.png" alt="FastAPI" width="100%">
</p>

# API

O [openapi.yaml](https://github.com/Solierrr/api-recommendation/blob/main/openapi.yaml) é o contrato completo. `/docs` e `/openapi.json` dependem de `DOCS_ENABLED`.

As rotas `/feeds/professionals`, `/feeds/offers` e `/feeds/suppliers` exigem a `X-Service-Key` do `mcp-database`, e o cabeçalho legado `X-Recommendation-Key` continua aceito quando está configurado. As rotas `/public/feeds/*` são públicas e nunca consultam o Neo4j.

```http
GET /feeds/offers?strategy=best_value
X-Service-Key: <chave do chamador>
```

O retorno privado traz `source`, o contexto, os itens e os avisos, e `source=fallback` indica que a estratégia pedida não foi aplicada. As listas públicas saem com cache público e `stale-if-error`.

Os erros usam o [catálogo](https://github.com/Solierrr/docs-warehouse/blob/main/docs/standards/ERROR_CODES.md). Destacam-se `LOCAL_UNIT_REQUIRED`, `LOCAL_UNIT_NOT_FOUND`, `LOCAL_UNIT_GEO_REQUIRED`, `LOCAL_UNIT_GEO_AMBIGUOUS`, `PROFESSION_NOT_FOUND`, `CANDIDATE_POOL_TOO_LARGE` e `FEED_UNAVAILABLE`.
