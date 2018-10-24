from jinja2.utils import Markup, escape
from srht.config import cfg
from srht.database import DbSession
from srht.flask import SrhtFlask, icon
from todosrht.urls import label_search_url, label_remove_url

db = DbSession(cfg("todo.sr.ht", "connection-string"))

from todosrht.types import User
from todosrht.types import TicketAccess, TicketStatus, TicketResolution

db.init()

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

def render_label_badge(label, cls="", remove_from_ticket=None):
    """Return HTML markup rendering a label badge.

    Additional HTML classes can be passed via the `cls` parameter.

    If a Ticket is passed in `remove_from_ticket`, a removal button will also
    be rendered for removing the label from given ticket.
    """
    style = f"color: {label.text_color}; background-color: {label.color}"
    html_class = f"label {cls}".strip()
    search_url = label_search_url(label)
    escaped_name = escape(label.name)

    if remove_from_ticket:
        remove_url = label_remove_url(label, remove_from_ticket)
        remove_form = f"""
            <form method="POST" action="{remove_url}">
              <button type="submit" class="btn btn-link">
                {icon('times')}
              </button>
            </form>
        """
    else:
        remove_form = ""

    return Markup(
        f"""<span style="{style}" class="{html_class}" href="{search_url}">
            <a href="{search_url}">{escaped_name}</a>
            {remove_form}
        </span>"""
    )

class TodoApp(SrhtFlask):
    def __init__(self):
        super().__init__("todo.sr.ht", __name__)

        self.url_map.strict_slashes = False

        from todosrht.blueprints.html import html
        from todosrht.blueprints.tracker import tracker
        from todosrht.blueprints.ticket import ticket

        self.register_blueprint(html)
        self.register_blueprint(tracker)
        self.register_blueprint(ticket)

        meta_client_id = cfg("todo.sr.ht", "oauth-client-id")
        meta_client_secret = cfg("todo.sr.ht", "oauth-client-secret")
        self.configure_meta_auth(meta_client_id, meta_client_secret)

        @self.context_processor
        def inject():
            return {
                "render_status": render_status,
                "TicketAccess": TicketAccess,
                "TicketStatus": TicketStatus,
                "TicketResolution": TicketResolution
            }

        @self.login_manager.user_loader
        def user_loader(username):
            # TODO: Switch to a session token
            return User.query.filter(User.username == username).one_or_none()

        @self.template_filter()
        def label_badge(label, **kwargs):
            return render_label_badge(label, **kwargs)

        @self.template_filter()
        def label_search_url(label):
            from todosrht.urls import label_search_url
            return Markup(label_search_url(label))

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
