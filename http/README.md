# Coleção Bruno: api-recommendation

Abra esta pasta `http/` como uma coleção Bruno e selecione o ambiente `local`.
A URL base é `http://localhost:8000`. Credenciais, tokens e chaves de API ficam vazios no ambiente versionado; preencha-os localmente no Bruno e não faça commit desses valores.

Os IDs usam UUIDs de exemplo sintaticamente válidos. Troque-os por IDs existentes no banco local quando a operação depender de dados prévios. Requests que criam, atualizam, removem, iniciam fluxos ou chamam rotas internas estão marcados no nome ou na documentação; confira seus efeitos antes de enviar. A coleção não executa requests automaticamente.

FastAPI's interactive docs/OpenAPI are conditional on the service setting `DOCS_ENABLED`; enable it in the local service configuration when needed.
