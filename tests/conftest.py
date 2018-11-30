import pytest
from srht.database import DbSession
from todosrht.flask import TodoApp

# In memory database
db = DbSession("sqlite://")
db.create()
db.init()

@pytest.fixture(scope="session", autouse=True)
def app():
    app = TodoApp()
    app.secret_key = "secret"
    with app.test_request_context():
        yield app

@pytest.fixture
def client(app):
    """Provides a test Flask client."""
    # Propagate view exceptions instead of returning HTTP 500
    app.testing = True
    with app.test_client() as client:
        yield client
