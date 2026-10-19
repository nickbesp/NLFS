import pytest
from fastapi.testclient import TestClient

from app import database
from app.main import app


@pytest.fixture()
def client(tmp_path):
    database.configure(tmp_path / "test.db")
    with TestClient(app) as c:
        yield c
