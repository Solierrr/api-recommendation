class FeedError(Exception):
    status_code = 500

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


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
