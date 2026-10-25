"""Exporta o contrato OpenAPI completo (com as rotas /internal/) para openapi.yaml."""

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Sobe só a camada web: sem .env, sem banco e sem segredo.
os.environ["APP_ENVIRONMENT"] = "test"
os.environ["DOCS_ENABLED"] = "true"
sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402

from app.main import app  # noqa: E402
from app.openapi import build_openapi  # noqa: E402


class _NoAliasDumper(yaml.SafeDumper):
    def ignore_aliases(self, data):
        return True


VERSION_LINE = re.compile(r"^(  version: .+)$", re.MULTILINE)


def main() -> None:
    contract = yaml.dump(
        build_openapi(app, include_internal=True),
        Dumper=_NoAliasDumper,
        sort_keys=False,
        allow_unicode=True,
        width=120,
    )
    contract = VERSION_LINE.sub(r"\1 # x-release-please-version", contract, count=1)
    (ROOT / "openapi.yaml").write_text(contract, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
