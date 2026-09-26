# Changelog

## [0.2.0](https://github.com/Solierrr/api-recommendation/compare/v0.1.0...v0.2.0) (2026-09-26)


### Features

* add minimal python app skeleton ([ebe22a9](https://github.com/Solierrr/api-recommendation/commit/ebe22a97a27281ce15ff688040b713a9eaa1e534))
* add Pydantic schemas for recommendations and telemetry events ([30af4a5](https://github.com/Solierrr/api-recommendation/commit/30af4a55b37d1c6aa14684b1c12ed0970c107026))
* add python makefile ([#35](https://github.com/Solierrr/api-recommendation/issues/35)) ([a7c9d62](https://github.com/Solierrr/api-recommendation/commit/a7c9d6202cbeacc0017387439709ea1e2d2fb4a9))
* add telemetry event repository and service layer ([b55ee3b](https://github.com/Solierrr/api-recommendation/commit/b55ee3beb57d6589def6d7632b144f44b185443a))
* **api:** expose secured recommendation and sync routes ([e42e355](https://github.com/Solierrr/api-recommendation/commit/e42e3556aa53e3afed603335c2d4ff1885068f98))
* expose POST /recommendations and POST /events endpoints ([56e4e8b](https://github.com/Solierrr/api-recommendation/commit/56e4e8bdfb6c4621074eadff154d2af4a6c60717))
* inject secrets via infisical run at container startup ([69c45e8](https://github.com/Solierrr/api-recommendation/commit/69c45e820cd6e85cf5204d4794edb9e3ab6d77f3))
* inject secrets via infisical run at container startup ([e2de9d4](https://github.com/Solierrr/api-recommendation/commit/e2de9d4bd30f51512448b945a7f71b2584fc853c))
* protect recommendations and events routes with X-API-Key header ([f666fba](https://github.com/Solierrr/api-recommendation/commit/f666fbaf7e13c3a64bf719ff65b6f4a787469de8))
* publish docker image on push to main ([8af2fd1](https://github.com/Solierrr/api-recommendation/commit/8af2fd178d47f1fc6712a3ed1557b350a5d2e557))
* publish docker image to docker hub on push to main ([8f5c3c9](https://github.com/Solierrr/api-recommendation/commit/8f5c3c9c8caa618d83dd8481c993d0f16da6d4b8))
* **recommendations:** add contextual ranking strategies ([323db28](https://github.com/Solierrr/api-recommendation/commit/323db282a6a743da7c1cdab16e193a7aadc5447e))
* **sync:** add versioned Neo4j graph synchronization ([7377e7b](https://github.com/Solierrr/api-recommendation/commit/7377e7bbe5654a7e0597668a57fd4baa19b80e39))
* wire up qa-sync and repo-cleanup reusable workflows ([1554ecd](https://github.com/Solierrr/api-recommendation/commit/1554ecd3aebab319f273463aa08e1611329441d9))
* wire up qa-sync and repo-cleanup reusable workflows ([9362651](https://github.com/Solierrr/api-recommendation/commit/9362651581bcd0dd5f5f6d2b1558b26db8c3c7df))


### Bug Fixes

* add missing CMD to start the FastAPI server ([4e8473b](https://github.com/Solierrr/api-recommendation/commit/4e8473b2aca3000416d4d118f49279a2f4da90c7))
* address SonarCloud findings on PR [#4](https://github.com/Solierrr/api-recommendation/issues/4) ([1b51464](https://github.com/Solierrr/api-recommendation/commit/1b51464f1965b308701465668df0f62c2e763ce4))
* adiciona hashes de seguranca no requirements ([d65aa23](https://github.com/Solierrr/api-recommendation/commit/d65aa23c83fdca533fd9b82d2f093a6fe86c2f74))
* **api:** preserve legacy contracts securely ([6d67647](https://github.com/Solierrr/api-recommendation/commit/6d676473835cb48f3a8b610c1084e45d4a069948))
* **ci:** reconcile hardening with base ([c67fa04](https://github.com/Solierrr/api-recommendation/commit/c67fa0466f24c30ba151fd5edc250b778cbdd4cb))
* **ci:** resolve locks for Linux ([13fffb3](https://github.com/Solierrr/api-recommendation/commit/13fffb3e8532adf0444e39149882e42bd1649639))
* **ci:** restore test and quality gates ([f572b40](https://github.com/Solierrr/api-recommendation/commit/f572b405c58104d9e85cd2c33b7d3dcf35c42c94))
* correct route registration, min_level propagation and error leakage ([684eb9a](https://github.com/Solierrr/api-recommendation/commit/684eb9ab970e64b4c57b5a2e5496118a9ed41a02))
* **deps:** add tzdata for zoneinfo on minimal runtimes ([f0f25f1](https://github.com/Solierrr/api-recommendation/commit/f0f25f17b3b3cbb2f82a1c4d1421e456398d5bac))
* **deps:** add tzdata for zoneinfo on minimal runtimes ([089e891](https://github.com/Solierrr/api-recommendation/commit/089e891d79d02986ceecd3bad937a4b3c22badda))
* exclude .github/** from SonarCloud analysis to suppress S8553 false positives on CI workflows ([ca62f2c](https://github.com/Solierrr/api-recommendation/commit/ca62f2cdc18913651ba85f06877c6ed551e71794))
* pass workflow run id when downloading coverage artifact for sonarqube ([7a1ed6d](https://github.com/Solierrr/api-recommendation/commit/7a1ed6d3e3a8af40568654d3d0e6b52d5388023a))
* pin dependencies and fix TLS verification against Neo4j AuraDB ([60c0f10](https://github.com/Solierrr/api-recommendation/commit/60c0f1023bd8c8645a59ecb65f43e7b80afd0bd8))
* pin pip version to suppress SonarCloud S8553 on CI workflows ([935c2ef](https://github.com/Solierrr/api-recommendation/commit/935c2ef611b8ed888e46205ae233240e2a80f868))
* **quality:** satisfy strict Ruff checks ([0208cb4](https://github.com/Solierrr/api-recommendation/commit/0208cb43d1b65c94a9253f02aa87592c3a0fc9b5))
* **recommendation:** drop unmodeled shift-based availability check ([2e4810a](https://github.com/Solierrr/api-recommendation/commit/2e4810adfcede19a1be46ecd5cef3eb0d15bb41a))
* support current infisical cli repository ([9e2284c](https://github.com/Solierrr/api-recommendation/commit/9e2284c042b21d5b0b9a577609d400cbb9e37ff0))
* **sync:** rewrite core_graph_repository queries for real schema ([6302fc5](https://github.com/Solierrr/api-recommendation/commit/6302fc55a21cc5a53676791fefc190af46793fdc))
* trigger releases by command ([1de0063](https://github.com/Solierrr/api-recommendation/commit/1de0063e9e9b742a30176e214060bfe22a7665f4))
* use --only-binary=:all: instead of --only-binary :all: to work around SonarCloud S8544 parser bug ([581a9b6](https://github.com/Solierrr/api-recommendation/commit/581a9b6ae4201e1f057f556499fa89cdf47a9767))
* use Annotated for FastAPI dependency injection in health.py ([f84ac3d](https://github.com/Solierrr/api-recommendation/commit/f84ac3de7a7a8309cd7ee9753105892e918826bb))
* use root path for infisical run ([e25b8f6](https://github.com/Solierrr/api-recommendation/commit/e25b8f6c2e3535fd21d39c8ee4b70b5255f890d3))
* use root path for infisical run to avoid identity folder scoping issue ([e017400](https://github.com/Solierrr/api-recommendation/commit/e017400200ba429bb4cc001ea0838ef2d251275a))
