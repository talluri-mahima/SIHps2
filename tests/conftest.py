import os
import uuid
import time
from pathlib import Path
import pytest

# Always isolate tests from the working demo database and evidence.
TEST_DATA = Path(__file__).resolve().parents[1] / '.data' / 'test-runs' / uuid.uuid4().hex
TEST_DATA.mkdir(parents=True, exist_ok=True)
os.environ['AICTE_DATA_DIR'] = str(TEST_DATA)
os.environ['AICTE_DATABASE_URL'] = f'sqlite:///{TEST_DATA / "test.db"}'
os.environ['APP_ENV'] = 'development'

from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app.db import Session
from app import models as m


@pytest.fixture(scope='session')
def server():
    with TestClient(app) as client:
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            with Session() as db:
                statuses = db.scalars(select(m.Job.status)).all()
            if statuses and all(s in {'COMPLETED', 'FAILED'} for s in statuses):
                break
            time.sleep(.1)
        else:
            raise AssertionError('Synthetic extraction did not finish')
        yield client


@pytest.fixture
def clients(server):
    result = {}
    for persona in ['officer', 'institution', 'auditor']:
        c = TestClient(app)
        assert c.post('/v1/dev/session/'+persona).status_code == 200
        result[persona] = c
    yield result
    for c in result.values():
        c.close()


@pytest.fixture
def fresh_app(clients):
    response = clients['institution'].post('/v1/applications', json={'name': 'Isolated synthetic test', 'category': 'NEW_INSTITUTION', 'evaluation_date': '2026-10-27'})
    assert response.status_code == 201
    return response.json()['id']
