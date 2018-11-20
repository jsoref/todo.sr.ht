from srht.config import cfg
from srht.database import DbSession
from todosrht.flask import TodoApp

db = DbSession(cfg("todo.sr.ht", "connection-string"))
db.init()

app = TodoApp()
