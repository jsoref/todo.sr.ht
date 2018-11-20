import pytest
from srht.database import DbSession
from todosrht.flask import TodoApp

# In memory database
db = DbSession("sqlite://")
db.create()
db.init()

@pytest.fixture(scope="session", autouse=True)
def app():
    return TodoApp()
