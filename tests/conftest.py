import pytest
from srht.database import DbSession
from todosrht.flask import TodoApp
from collections import namedtuple

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

# Stores sent emails
_mailbox = []

Email = namedtuple("Email", ["body", "to", "subject", "headers"])

@pytest.fixture()
def mailbox(monkeypatch):
    """Intercepts calls to send_email and provides them via fixture."""
    def mock_send_email(body, to, subject, encrypt_key=None, **headers):
        _mailbox.append(Email(body, to, subject, headers))

    monkeypatch.setattr('todosrht.email.send_email', mock_send_email)
    monkeypatch.setattr('todosrht.email.lookup_key', lambda *args: None)

    _mailbox = []  # Clear on each mock
    return _mailbox

@pytest.fixture()
def no_emails(monkeypatch):
    """Discards all emails sent by tested code."""
    monkeypatch.setattr('todosrht.email.send_email', lambda *a, **k: None)
    monkeypatch.setattr('todosrht.email.lookup_key', lambda *a, **k: None)
