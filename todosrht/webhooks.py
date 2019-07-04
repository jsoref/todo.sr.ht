from srht.config import cfg
from srht.database import DbSession, db
if not hasattr(db, "session"):
    # Initialize the database if not already configured (for running daemon)
    db = DbSession(cfg("todo.sr.ht", "connection-string"))
    import todosrht.types
    db.init()
from srht.webhook import Event
from srht.webhook.celery import CeleryWebhook, make_worker
import sqlalchemy as sa

worker = make_worker(broker=cfg("todo.sr.ht", "webhooks"))

class UserWebhook(CeleryWebhook):
    events = [
        Event("tracker:create", "trackers:read"),
        Event("tracker:update", "trackers:read"),
        Event("tracker:delete", "trackers:read"),
        Event("ticket:create", "tickets:read"),
    ]

class TrackerWebhook(CeleryWebhook):
    events = [
        Event("label:create", "trackers:read"),
        Event("label:delete", "trackers:read"),
        Event("ticket:create", "tickets:read"),
        Event("event:create", "tickets:read"),
    ]

    tracker_id = sa.Column(sa.Integer,
            sa.ForeignKey('tracker.id'), nullable=False)
    tracker = sa.orm.relationship('Tracker')

class TicketWebhook(CeleryWebhook):
    events = [
        Event("ticket:update", "tickets:read"),
        Event("event:create", "tickets:read"),
    ]

    ticket_id = sa.Column(sa.Integer,
            sa.ForeignKey('ticket.id'), nullable=False)
    ticket = sa.orm.relationship('Ticket')