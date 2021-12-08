from srht.config import cfg
from srht.database import DbSession, db
if not hasattr(db, "session"):
    # Initialize the database if not already configured (for running daemon)
    db = DbSession(cfg("todo.sr.ht", "connection-string"))
    import todosrht.types
    db.init()
from srht.webhook import Event
from srht.webhook.celery import CeleryWebhook, make_worker
from srht.metrics import RedisQueueCollector
import sqlalchemy as sa


webhooks_broker = cfg("todo.sr.ht", "webhooks")
worker = make_worker(broker=webhooks_broker)
webhook_metrics_collector = RedisQueueCollector(webhook_broker, "srht_webhooks", "Webhook queue length")

import todosrht.tracker_import

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
            sa.ForeignKey('tracker.id', ondelete="CASCADE"), nullable=False)
    tracker = sa.orm.relationship('Tracker', cascade="all, delete-orphan")

class TicketWebhook(CeleryWebhook):
    events = [
        Event("ticket:update", "tickets:read"),
        Event("event:create", "tickets:read"),
    ]

    ticket_id = sa.Column(sa.Integer,
            sa.ForeignKey('ticket.id', ondelete="CASCADE"), nullable=False)
    ticket = sa.orm.relationship('Ticket', cascade="all, delete-orphan")

