class RecommendationError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class SnapshotUnavailableError(RecommendationError):
    pass


class ContextNotFoundError(RecommendationError):
    pass


class RecommendationDataUnavailableError(RecommendationError):
    pass


class SyncInProgressError(RuntimeError):
    pass


class UnsafeSnapshotError(RuntimeError):
    pass
