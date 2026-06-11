import pytest
from pathlib import Path

@pytest.fixture(autouse=True)
def tmp_db(monkeypatch, tmp_path):
    """Redirect DB_PATH to a temp file for every test."""
    db_file = tmp_path / "test.db"
    monkeypatch.setattr("db.schema.DB_PATH", db_file)
    yield db_file
