import json
import pytest
import sys
import os
# Ensure project root is on sys.path so tests can import app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app as flask_app

@pytest.fixture
def client():
    with flask_app.test_client() as c:
        yield c

def test_index(client):
    rv = client.get('/')
    assert rv.status_code == 200
    text = rv.data.decode('utf-8', errors='ignore')
    assert "SweetSeek" in text or "搜索" in text

def test_static_pages(client):
    for path in ['/search.html', '/management.html', '/about.html', '/upload.html']:
        rv = client.get(path)
        assert rv.status_code == 200

def test_api_stats_and_conversations(client):
    rv = client.get('/api/stats')
    assert rv.status_code == 200
    data = rv.get_json()
    assert data.get('success', True) is True

    rv2 = client.get('/api/conversations')
    assert rv2.status_code == 200
    data2 = rv2.get_json()
    assert data2.get('success') is True
    assert isinstance(data2.get('conversations'), list)
