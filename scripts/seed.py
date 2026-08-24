"""Povoa o grafo do Neo4j com a massa de dados de teste do MVP.

Lê scripts/seed.cypher, divide em declarações individuais (o driver do Neo4j
não aceita múltiplas declarações Cypher separadas por ';' em uma única
chamada, diferente do console/cypher-shell) e executa cada uma em sequência,
dentro de uma única transação.

ATENÇÃO: a primeira declaração do script (MATCH (n) DETACH DELETE n) apaga
TODOS os nós e relacionamentos do banco de dados configurado em NEO4J_URI
antes de recriar a massa de dados. Use apenas em bancos de desenvolvimento
ou de teste, nunca em produção com dados reais.

Uso:
    python scripts/seed.py
"""

import asyncio
import sys
from pathlib import Path

# Permite executar `python scripts/seed.py` a partir da raiz do projeto,
# importando os módulos de app/ (config, database) sem precisar instalar
# o projeto como pacote.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings  # noqa: E402
from app.database import neo4j_service  # noqa: E402

SEED_FILE = Path(__file__).resolve().parent / "seed.cypher"


def load_statements() -> list[str]:
    """Lê o arquivo .cypher e devolve a lista de declarações não vazias,
    ignorando linhas de comentário (// ...)."""
    raw = SEED_FILE.read_text(encoding="utf-8")
    statements = []
    for chunk in raw.split(";"):
        lines = [
            line
            for line in chunk.splitlines()
            if line.strip() and not line.strip().startswith("//")
        ]
        statement = "\n".join(lines).strip()
        if statement:
            statements.append(statement)
    return statements


async def run_seed() -> None:
    statements = load_statements()
    print(f"Conectando em {settings.NEO4J_URI} ...")
    await neo4j_service.connect()
    try:
        async with neo4j_service._driver.session() as session:
            async with await session.begin_transaction() as tx:
                for i, statement in enumerate(statements, start=1):
                    print(f"[{i}/{len(statements)}] executando: {statement.splitlines()[0][:70]}...")
                    await tx.run(statement)
                await tx.commit()
        print(f"Seed concluído com sucesso. {len(statements)} declarações executadas.")
    finally:
        await neo4j_service.close()


if __name__ == "__main__":
    asyncio.run(run_seed())
