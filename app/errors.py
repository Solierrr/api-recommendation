from app.observability.errors import ApiError


class FeedError(ApiError):
    """Erro de feed com status próprio -> o handler global de ApiError devolve o ProblemDetail

    code vira errorCode no corpo | status_code vira o status HTTP | message segue como detail
    """

    status_code = 500

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.status = self.status_code
        self.error_code = code


class ContextNotFoundError(FeedError):
    status_code = 404


class FeedDataUnavailableError(FeedError):
    status_code = 422


class FeedUnavailableError(FeedError):
    status_code = 503


class GraphUnavailableError(Exception):
    pass


class SnapshotUnavailableError(GraphUnavailableError):
    pass
