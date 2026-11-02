<p align="center">
  <img src="../assets/readme/banners/fastapi.png" alt="FastAPI" width="100%">
</p>

# Critérios de ordenação

As [estratégias](https://github.com/Solierrr/api-recommendation/tree/main/app/feeds) produzem métricas e motivos por item.

| Domínio | Critério implementado |
|---|---|
| Profissionais | Avaliação bayesiana com peso prévio de cinco avaliações. Confiabilidade combina 60% de conclusão e 40% de avaliação ajustada. |
| Melhor combinação profissional | 40% avaliação, 25% certificações normalizadas, 20% experiência normalizada e 15% confiabilidade. |
| Ofertas | Preço em reais por Wp, eficiência, distância Haversine ou quantidade em propostas aceitas. |
| Fornecedores | Quantidade em propostas aceitas, número de ofertas elegíveis ou distância Haversine. |

As ofertas só entram com modelo aprovado, fornecedor ativo com assinatura ativa, preço positivo, disponibilidade e validade, os profissionais precisam de usuário ativo e os fornecedores precisam ter ofertas elegíveis.

O ranking tem limite de candidatos para evitar ordenar apenas parte de um conjunto global. Os desempates usam métricas auxiliares e identificadores definidos em cada estratégia. O fallback sorteia uma amostra do conjunto SQL selecionado, sem reproduzir o ranking do grafo.
