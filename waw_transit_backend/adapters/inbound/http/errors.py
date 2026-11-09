from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from waw_transit.core import RepositoryError
from waw_transit_backend.domain import NotFoundError, UpstreamUnavailableError


def register_error_handlers(app: FastAPI) -> None:

    @app.exception_handler(NotFoundError)
    def _not_found(request: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(UpstreamUnavailableError)
    def _upstream_unavailable(request: Request, exc: UpstreamUnavailableError) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": str(exc)})

    @app.exception_handler(RepositoryError)
    def _repository_error(request: Request, exc: RepositoryError) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": str(exc)})
