from datetime import datetime

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel, Field

PROBLEM_MEDIA_TYPE = "application/problem+json"
FASTAPI_VALIDATION_SCHEMAS = ("HTTPValidationError", "ValidationError")


class ProblemFieldError(BaseModel):
    field: str = Field(description="Campo ou parâmetro inválido.", examples=["profession_id"])
    errorCode: str = Field(description="Código estável do erro.", examples=["VALIDATION_FAILED"])
    detail: str = Field(description="Explicação para quem depura.", examples=["Input should be a valid UUID"])


class ProblemDetail(BaseModel):
    type: str = Field(description="Sempre about:blank.", examples=["about:blank"])
    title: str = Field(description="O mesmo valor de errorCode.", examples=["PROFESSION_NOT_FOUND"])
    status: int = Field(description="Código HTTP.", examples=[404])
    errorCode: str = Field(
        description="Código estável do catálogo de erros.", examples=["PROFESSION_NOT_FOUND"]
    )
    detail: str = Field(
        description="Explicação para quem depura; o front não exibe.",
        examples=["A profissão não existe no snapshot ativo."],
    )
    instance: str = Field(description="Caminho da requisição.", examples=["/feeds/professionals"])
    timestamp: datetime = Field(description="Momento do erro, em UTC.")
    traceId: str | None = Field(default=None, description="Id do trace, quando houver.")
    errors: list[ProblemFieldError] | None = Field(
        default=None, description="Campos inválidos, só em validação."
    )


def _problem_schemas() -> dict:
    schema = ProblemDetail.model_json_schema(ref_template="#/components/schemas/{model}")
    definitions = schema.pop("$defs", {})
    return {**definitions, "ProblemDetail": schema}


def _uses_fastapi_validation(response: dict) -> bool:
    schema = response.get("content", {}).get("application/json", {}).get("schema", {})
    return schema.get("$ref", "").endswith("/HTTPValidationError")


def _apply_problem_detail(schema: dict) -> None:
    components = schema.setdefault("components", {})
    schemas = components.setdefault("schemas", {})
    schemas.update(_problem_schemas())
    problem = {PROBLEM_MEDIA_TYPE: {"schema": {"$ref": "#/components/schemas/ProblemDetail"}}}
    for path in schema["paths"].values():
        for operation in path.values():
            responses = operation["responses"]
            responses.setdefault("500", {"description": "Erro interno inesperado."})
            for code, response in responses.items():
                if code[0] in "45" and ("content" not in response or _uses_fastapi_validation(response)):
                    response["content"] = problem
    for name in FASTAPI_VALIDATION_SCHEMAS:
        schemas.pop(name, None)


def build_openapi(app: FastAPI, include_internal: bool) -> dict:
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=app.openapi_tags,
        servers=app.servers,
        contact=app.contact,
        license_info=app.license_info,
    )
    schema["security"] = [{"serviceKey": []}]
    _apply_problem_detail(schema)
    if not include_internal:
        schema["paths"] = {
            path: item for path, item in schema["paths"].items() if not path.startswith("/internal/")
        }
        used = {
            tag
            for item in schema["paths"].values()
            for operation in item.values()
            for tag in operation.get("tags", [])
        }
        schema["tags"] = [tag for tag in schema.get("tags", []) if tag["name"] in used]
    return schema


def install_openapi(app: FastAPI) -> None:
    def public_openapi() -> dict:
        if app.openapi_schema is None:
            app.openapi_schema = build_openapi(app, include_internal=False)
        return app.openapi_schema

    app.openapi = public_openapi  # type: ignore[method-assign]
