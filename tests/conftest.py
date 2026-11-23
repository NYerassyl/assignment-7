import os
import secrets
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import make_url
from sqlalchemy import text
from database import engine
from main import app


@pytest.fixture
def client(monkeypatch):
    url = make_url(os.environ['DATABASE_URL'])
    if url.host not in (None, 'localhost', '127.0.0.1') or not url.database.endswith('_test'):
        pytest.fail('Tests require an isolated localhost database ending in _test')
    monkeypatch.setenv('JWT_SECRET', secrets.token_urlsafe(48))
    monkeypatch.setenv('JWT_ACCESS_TTL_SECONDS', '3600')
    with engine().begin() as db:
        db.execute(text('TRUNCATE "AuthSession", "User" CASCADE'))
    with TestClient(app) as http:
        yield http


@pytest.fixture
def register(client):
    def create(name='alice'):
        response = client.post('/api/auth/register', json={
            'email': name+'@example.com', 'nickname': name, 'password': 'StrongPassword123!'})
        assert response.status_code == 201, response.text
        data = response.json()
        return data, {'Authorization': 'Bearer '+data['token']}
    return create
