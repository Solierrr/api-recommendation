from app.database import GraphService, PostgresService, graph_service, postgres_service


def get_graph() -> GraphService:
    return graph_service


def get_postgres() -> PostgresService:
    return postgres_service
