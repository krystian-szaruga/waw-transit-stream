from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from waw_transit_backend.composition.app import create_app


@pytest.fixture
def app() -> FastAPI:
    return create_app()


@pytest.fixture
def client(app: FastAPI, postgres: None, redis_store: None) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client
