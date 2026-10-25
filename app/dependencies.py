from app.database import GraphService, graph_service


def get_graph() -> GraphService:
    return graph_service
