from jinja2 import Markup
from srht.flask import SrhtFlask
from srht.config import cfg, load_config
load_config("todo")

from srht.database import DbSession
db = DbSession(cfg("sr.ht", "connection-string"))

from todosrht.types import User
from todosrht.types import TicketAccess, TicketStatus, TicketResolution
from todosrht.types import TicketSeen
db.init()

from todosrht.blueprints.html import html
from todosrht.blueprints.tracker import tracker
from todosrht.blueprints.ticket import ticket

def tracker_name(tracker, full=False):
    split = tracker.name.split("/")
    user = tracker.owner.canonical_name()
    if full:
        return Markup(
            "/".join(["<a href='/{0}'>{0}</a>".format(user)] + [
                "<a href='/{}/{}'>{}</a>".format(user, "/".join(split[:i + 1]), p)
                for i, p in enumerate(split)
        ]))
    name = split[-1]
    if len(name) == 0:
        return name
    parts = split[:-1]
    return Markup(
        "/".join(["<a href='/{0}'>{0}</a>".format(user)] + [
            "<a href='/{}/{}'>{}</a>".format(user, "/".join(parts[:i + 1]), p)
            for i, p in enumerate(parts)
        ]) + "/" + name
    )

def render_status(ticket, access):
    if TicketAccess.edit in access:
        return Markup(
            "<select name='status'>" +
            "".join([
                "<option value='{0}' {1}>{0}</option>".format(s.name,
                    "selected" if ticket.status == s else "")
                for s in TicketStatus
            ]) +
            "</select>"
        )
    else:
        return "<span>{}</span>".format(ticket.status.name)

class TodoApp(SrhtFlask):
    def __init__(self):
        super().__init__("todo", __name__)

        self.url_map.strict_slashes = False

        self.register_blueprint(html)
        self.register_blueprint(tracker)
        self.register_blueprint(ticket)

        meta_client_id = cfg("meta.sr.ht", "oauth-client-id")
        meta_client_secret = cfg("meta.sr.ht", "oauth-client-secret")
        self.configure_meta_auth(meta_client_id, meta_client_secret)

        @self.context_processor
        def inject():
            return {
                "format_tracker_name": tracker_name,
                "render_status": render_status,
                "TicketAccess": TicketAccess,
                "TicketStatus": TicketStatus,
                "TicketResolution": TicketResolution
            }

        @self.login_manager.user_loader
        def user_loader(username):
            # TODO: Switch to a session token
            return User.query.filter(User.username == username).one_or_none()

    def lookup_or_register(self, exchange, profile, scopes):
        user = User.query.filter(User.username == profile["username"]).first()
        if not user:
            user = User()
            db.session.add(user)
        user.username = profile.get("username")
        user.email = profile.get("email")
        user.oauth_token = exchange["token"]
        user.oauth_token_expires = exchange["expires"]
        user.oauth_token_scopes = scopes
        db.session.commit()
        return user

app = TodoApp()
