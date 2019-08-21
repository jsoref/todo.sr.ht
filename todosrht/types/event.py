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
    assigned_user = 32
    unassigned_user = 64
    user_mentioned = 128
    ticket_mentioned = 256

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

    participant_id = sa.Column(sa.Integer, sa.ForeignKey("participant.id"))
    participant = sa.orm.relationship("Participant",
            backref=sa.orm.backref("events"), foreign_keys=[participant_id])

    ticket_id = sa.Column(sa.Integer,
            sa.ForeignKey("ticket.id", ondelete="CASCADE"))
    ticket = sa.orm.relationship("Ticket",
            foreign_keys=[ticket_id],
            backref=sa.orm.backref("events", cascade="all, delete-orphan"))

    comment_id = sa.Column(sa.Integer,
            sa.ForeignKey("ticket_comment.id", ondelete="CASCADE"))
    comment = sa.orm.relationship("TicketComment", cascade="all, delete")

    label_id = sa.Column(sa.Integer,
            sa.ForeignKey('label.id', ondelete="CASCADE"))
    label = sa.orm.relationship("Label",
            backref=sa.orm.backref("events", cascade="all, delete-orphan"))

    by_participant_id = sa.Column(sa.Integer, sa.ForeignKey("participant.id"))
    by_participant = sa.orm.relationship(
            "Participant", foreign_keys=[by_participant_id])

    from_ticket_id = sa.Column(sa.Integer,
            sa.ForeignKey("ticket.id", ondelete="CASCADE"))
    from_ticket = sa.orm.relationship("Ticket", foreign_keys=[from_ticket_id])

    def __repr__(self):
        return '<Event {}>'.format(self.id)

    def to_dict(self):
        return {
            "id": self.id,
            "created": self.created,
            "event_type": [t.name for t in EventType if t in self.event_type],
            "old_status": self.old_status.name if self.old_status else None,
            "old_resolution": self.old_resolution.name
                if self.old_resolution else None,
            "new_status": self.new_status.name if self.new_status else None,
            "new_resolution": self.new_resolution.name
                if self.new_resolution else None,
            "user": self.participant.to_dict(short=True)
                if self.participant else None,
            "ticket": self.ticket.to_dict(short=True)
                if self.ticket else None,
            "comment": self.comment.to_dict(short=True)
                if self.comment else None,
            "label": self.label.name if self.label else None,
            "by_user": self.by_participant.to_dict(short=True)
                if self.by_participant else None,
            "from_ticket": self.from_ticket.to_dict(short=True)
                if self.from_ticket else None,
        }

class EventNotification(Base):
    __tablename__ = 'event_notification'
    id = sa.Column(sa.Integer, primary_key=True)
    created = sa.Column(sa.DateTime, nullable=False)

    event_id = sa.Column(sa.Integer,
            sa.ForeignKey("event.id", ondelete="CASCADE"),
            nullable=False)
    event = sa.orm.relationship("Event",
            backref=sa.orm.backref("notifications",
                cascade="all, delete-orphan"))

    user_id = sa.Column(sa.Integer,
            sa.ForeignKey("user.id"),
            nullable=False)
    user = sa.orm.relationship("User",
            backref=sa.orm.backref("notifications",
                cascade="all, delete-orphan"))

    def __repr__(self):
        return '<EventNotification {} {}>'.format(self.id, self.user.username)
