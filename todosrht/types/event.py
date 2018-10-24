import sqlalchemy as sa
from srht.flagtype import FlagType
from srht.database import Base
from todosrht.types.ticketstatus import TicketStatus, TicketResolution
from enum import IntFlag

class EventType(IntFlag):
    created = 1
    comment = 2
    status_change = 4
    label_added = 8
    label_removed = 16

class Event(Base):
    """
    Maps events on tickets to interested users.
    """
    __tablename__ = 'event'
    id = sa.Column(sa.Integer, primary_key=True)
    created = sa.Column(sa.DateTime, nullable=False)

    event_type = sa.Column(FlagType(EventType), nullable=False)

    old_status = sa.Column(FlagType(TicketStatus), default=0)
    old_resolution = sa.Column(FlagType(TicketResolution), default=0)

    new_status = sa.Column(FlagType(TicketStatus), default=0)
    new_resolution = sa.Column(FlagType(TicketResolution), default=0)

    user_id = sa.Column(sa.Integer, sa.ForeignKey("user.id"), nullable=False)
    user = sa.orm.relationship("User", backref=sa.orm.backref("events"))

    ticket_id = sa.Column(sa.Integer, sa.ForeignKey("ticket.id"), nullable=False)
    ticket = sa.orm.relationship("Ticket")

    comment_id = sa.Column(sa.Integer, sa.ForeignKey("ticket_comment.id"))
    comment = sa.orm.relationship("TicketComment")

    label_id = sa.Column(sa.Integer, sa.ForeignKey('label.id'))
    label = sa.orm.relationship("Label", backref=sa.orm.backref("events"))

    def __repr__(self):
        return '<Event {}>'.format(self.id)

class EventNotification(Base):
    __tablename__ = 'event_notification'
    id = sa.Column(sa.Integer, primary_key=True)
    created = sa.Column(sa.DateTime, nullable=False)

    event_id = sa.Column(sa.Integer, sa.ForeignKey("event.id"), nullable=False)
    event = sa.orm.relationship("Event", backref=sa.orm.backref("notifications"))

    user_id = sa.Column(sa.Integer, sa.ForeignKey("user.id"), nullable=False)
    user = sa.orm.relationship("User", backref=sa.orm.backref("notifications"))

    def __repr__(self):
        return '<EventNotification {} {}>'.format(self.id, self.user.username)
