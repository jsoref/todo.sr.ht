from flask import render_template, request
from flask_login import LoginManager, current_user
from jinja2 import Markup
import locale
import urllib

from srht.config import cfg, cfgi, load_config
load_config("todo")
from srht.database import DbSession
db = DbSession(cfg("sr.ht", "connection-string"))
from todosrht.types import User, TicketAccess, TicketStatus, TicketResolution, TicketSeen
db.init()

from srht.flask import SrhtFlask
app = SrhtFlask("todo", __name__)
app.secret_key = cfg("server", "secret-key")
login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(username):
    return User.query.filter(User.username == username).first()

login_manager.anonymous_user = lambda: None

try:
    locale.setlocale(locale.LC_ALL, 'en_US')
except:
    pass

def oauth_url(return_to):
    return "{}/oauth/authorize?client_id={}&scopes=profile&state={}".format(
        meta_sr_ht, meta_client_id, urllib.parse.quote_plus(return_to))

from todosrht.blueprints.html import html
from todosrht.blueprints.auth import auth
from todosrht.blueprints.tracker import tracker

app.register_blueprint(html)
app.register_blueprint(auth)
app.register_blueprint(tracker)

meta_sr_ht = cfg("network", "meta")
meta_client_id = cfg("meta.sr.ht", "oauth-client-id")

def tracker_name(tracker, full=False):
    split = tracker.name.split("/")
    user = "~" + tracker.owner.username
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

@app.context_processor
def inject():
    return {
        "oauth_url": oauth_url(request.full_path),
        "current_user": User.query.filter(User.id == current_user.id).first() \
                if current_user else None,
        "format_tracker_name": tracker_name,
        "render_status": render_status,
        "TicketAccess": TicketAccess,
        "TicketStatus": TicketStatus,
        "TicketResolution": TicketResolution
    }
