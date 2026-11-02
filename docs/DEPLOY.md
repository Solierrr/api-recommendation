<p align="center">
  <img src="../assets/readme/banners/fastapi.png" alt="FastAPI" width="100%">
</p>

# Deploy

O [workflow de ambiente](https://github.com/Solierrr/api-recommendation/blob/main/.github/workflows/environment-status.yml) declara QA em https://api-recommendation-qlml.onrender.com e verificação de cluster de produção. Ele não informa uma URL pública de produção.

O processo comum está em [QA_RENDER.md](https://github.com/Solierrr/docs-warehouse/blob/main/readme/deploy/QA_RENDER.md) e [PROD_GKE_ARGOCD.md](https://github.com/Solierrr/docs-warehouse/blob/main/readme/deploy/PROD_GKE_ARGOCD.md). O container usa Python 3.12, dependências fixadas por hash e um usuário sem privilégios, e o `entrypoint.sh` inicia o runtime.

Em produção, o código exige SSL de PostgreSQL com `require` ou superior, documentação pública desligada e chave de serviço configurada, e o serviço está publicado no QA e na produção.
