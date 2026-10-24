"""Fixtures de pytest.

Cada corrida arranca con una base SQLite nueva y las semillas aplicadas,
asi la verificacion es reproducible: 2 tenants, 3 planes, 1 superadmin.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

# El backend corre con PYTHONPATH apuntando a su carpeta (no al monorepo),
# por eso insertamos la carpeta del backend en sys.path antes de importar.
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


@pytest.fixture(scope="session")
def _db_path(tmp_path_factory):
    d = tmp_path_factory.mktemp("saas-db")
    return d / "test.db"


@pytest.fixture(scope="session", autouse=True)
def _set_env(_db_path):
    os.environ["DATABASE_URL"] = f"sqlite:///{_db_path.as_posix()}"
    os.environ["JWT_SECRET"] = "test-secret"
    # Limpiamos cache de settings y re-cargamos la app con la URL de test.
    from app.core import config as _config
    _config.get_settings.cache_clear()
    yield


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.seeds.demo import run as seed_run

    # Re-crea la DB desde cero por test (barato con SQLite file).
    from app.core.database import Base, engine
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    seed_run()
    with TestClient(app) as c:
        yield c


def _auth(client, codigo_tenant: str, email: str, password: str) -> str:
    r = client.post(
        "/api/v1/auth/login",
        json={"codigo_tenant": codigo_tenant, "email": email, "password": password},
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _auth_super(client, email: str, password: str) -> str:
    r = client.post("/api/v1/auth/super/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture()
def token_luna(client):
    return _auth(client, "luna", "ana@boutique-luna.bo", "Luna12345")


@pytest.fixture()
def token_andina(client):
    return _auth(client, "andina", "rodrigo@modaandina.bo", "Andina12345")


@pytest.fixture()
def token_super(client):
    return _auth_super(client, "root@plataforma.bo", "SuperSegura123")


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# Reexpuesto para los tests
pytest.auth_headers = auth_headers  # type: ignore[attr-defined]
