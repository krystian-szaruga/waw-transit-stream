class BackendError(RuntimeError):
    pass


class NotFoundError(BackendError):
    pass


class UpstreamUnavailableError(BackendError):
    pass
