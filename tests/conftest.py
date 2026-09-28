import os
import sys
import tempfile

import pytest

# Ensure repo root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Point DB_PATH at a temp file BEFORE importing app (app.py runs init_db()/seed_db()
# at import time, and get_db() reads DB_PATH at call time). This keeps tests from
# ever touching the real spendly.db.
import database.db as db_module

_initial_fd, _initial_path = tempfile.mkstemp(suffix=".db")
os.close(_initial_fd)
db_module.DB_PATH = _initial_path

import app as app_module  # noqa: E402  (must be imported after DB_PATH patch)


@pytest.fixture
def app(tmp_path, monkeypatch):
    """Flask app wired to a fresh, isolated SQLite DB file per test."""
    db_path = tmp_path / "spendly-test.db"
    monkeypatch.setattr(db_module, "DB_PATH", str(db_path))

    app_module.app.config.update({
        "TESTING": True,
        "SECRET_KEY": "test-secret",
        "WTF_CSRF_ENABLED": False,
    })

    with app_module.app.app_context():
        db_module.init_db()
        db_module.seed_db()

    yield app_module.app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def seed_user_id(app):
    """The id of the seeded demo user (demo@spendly.com)."""
    user = db_module.get_user_by_email("demo@spendly.com")
    return user["id"]


@pytest.fixture
def auth_client(client):
    """A test client logged in as the seeded demo user."""
    client.post("/login", data={"email": "demo@spendly.com", "password": "demo123"})
    return client
