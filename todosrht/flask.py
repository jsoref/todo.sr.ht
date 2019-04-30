from srht.config import cfg
from srht.database import db
from srht.flask import SrhtFlask
from srht.oauth import AbstractOAuthService
from todosrht import urls, filters
from todosrht.service import TodoOAuthService
from todosrht.types import EventType
from todosrht.types import TicketAccess, TicketStatus, TicketResolution, User

class TodoApp(SrhtFlask):
    def __init__(self):
        super().__init__("todo.sr.ht", __name__,
                oauth_service=TodoOAuthService())

        self.url_map.strict_slashes = False

        from todosrht.blueprints.api import register_api
        from todosrht.blueprints.html import html
        from todosrht.blueprints.tracker import tracker
        from todosrht.blueprints.ticket import ticket

        register_api(self)
        self.register_blueprint(html)
        self.register_blueprint(tracker)
        self.register_blueprint(ticket)

        self.add_template_filter(filters.label_badge)
        self.add_template_filter(filters.render_comment)
        self.add_template_filter(filters.render_ticket_description)
        self.add_template_filter(urls.label_add_url)
        self.add_template_filter(urls.label_search_url)
        self.add_template_filter(urls.ticket_assign_url)
        self.add_template_filter(urls.ticket_edit_url)
        self.add_template_filter(urls.ticket_unassign_url)
        self.add_template_filter(urls.ticket_url)
        self.add_template_filter(urls.tracker_labels_url)
        self.add_template_filter(urls.tracker_url)
        self.add_template_filter(urls.user_url)

        @self.context_processor
        def inject():
            return {
                "EventType": EventType,
                "TicketAccess": TicketAccess,
                "TicketStatus": TicketStatus,
                "TicketResolution": TicketResolution
            }
