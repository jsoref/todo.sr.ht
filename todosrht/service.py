from todosrht.types import User, OAuthToken
from srht.database import db
from srht.config import cfg, get_origin
from srht.oauth import AbstractOAuthService, DelegatedScope

origin = cfg("todo.sr.ht", "origin")
client_id = cfg("todo.sr.ht", "oauth-client-id")
client_secret = cfg("todo.sr.ht", "oauth-client-secret")

class TodoOAuthService(AbstractOAuthService):
    def __init__(self):
        super().__init__(client_id, client_secret,
                delegated_scopes=[
                    DelegatedScope("events", "events", False),
                    DelegatedScope("trackers", "trackers", True),
                    DelegatedScope("tickets", "tickets", True),
                ],
                token_class=OAuthToken, user_class=User)
