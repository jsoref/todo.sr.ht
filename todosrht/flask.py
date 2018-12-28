from srht.config import cfg
from srht.database import db
from srht.flask import SrhtFlask
from todosrht import urls, filters
from todosrht.types import EventType
from todosrht.types import TicketAccess, TicketStatus, TicketResolution
from todosrht.types import User, UserType


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

        self.add_template_filter(filters.label_badge)
        self.add_template_filter(urls.label_search_url)
        self.add_template_filter(urls.ticket_assign_url)
        self.add_template_filter(urls.ticket_edit_url)
        self.add_template_filter(urls.ticket_unassign_url)
        self.add_template_filter(urls.ticket_url)
        self.add_template_filter(urls.tracker_labels_url)
        self.add_template_filter(urls.tracker_url)
        self.add_template_filter(urls.user_url)

        meta_client_id = cfg("todo.sr.ht", "oauth-client-id")
        meta_client_secret = cfg("todo.sr.ht", "oauth-client-secret")
        self.configure_meta_auth(meta_client_id, meta_client_secret)

        @self.context_processor
        def inject():
            return {
                "EventType": EventType,
                "TicketAccess": TicketAccess,
                "TicketStatus": TicketStatus,
                "TicketResolution": TicketResolution
            }

        @self.login_manager.user_loader
        def user_loader(username):
            # TODO: Switch to a session token
            return User.query.filter(User.username == username).one_or_none()

    def lookup_or_register(self, exchange, profile, scopes):
        user = User.query.filter(User.username == profile["name"]).first()
        if not user:
            user = User()
            db.session.add(user)
        user.username = profile["name"]
        user.email = profile["email"]
        user.user_type = UserType(profile["user_type"])
        user.oauth_token = exchange["token"]
        user.oauth_token_expires = exchange["expires"]
        user.oauth_token_scopes = scopes
        db.session.commit()
        return user
