<p align="center">
  <img src="../assets/readme/banners/fastapi.png" alt="FastAPI" width="100%">
</p>

# Consulta de recomendações

O feed de `offers` classifica os candidatos por preço por Wp, eficiência, distância ou adoção comercial. O [fluxo central](https://github.com/Solierrr/docs-warehouse/blob/main/docs/flows/RECOMMENDATION_FEED.md) descreve a produção do snapshot.

```mermaid
sequenceDiagram
 participant C as Chamador
 participant A as API
 participant G as Neo4j
 participant P as PostgreSQL
 C->>A: HTTP GET com X-Service-Key
 A->>G: Snapshot ativo e candidatos
 alt Grafo disponível
 G-->>A: Candidatos elegíveis
 A->>A: Aplica estratégia e limite
 else Grafo indisponível ou sem snapshot
 A->>P: Consulta amostra SQL
 P-->>A: Itens elegíveis
 end
 A-->>C: Itens, origem e avisos
```

Chave ausente ou inválida produz 401. Contexto inexistente produz 404, e contexto insuficiente ou conjunto acima do limite produz 422. Indisponibilidade das fontes necessárias produz 503. A rota pública usa somente PostgreSQL, sem chave ou etapa de ranking do grafo.
