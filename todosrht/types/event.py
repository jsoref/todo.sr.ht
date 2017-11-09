import sqlalchemy as sa
import sqlalchemy_utils as sau
from srht.flagtype import FlagType
from srht.database import Base
from todosrht.types.ticketstatus import TicketStatus, TicketResolution
from enum import IntFlag

class EventType(IntFlag):
    created = 1
    comment = 2
    status_change = 4

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

    def __repr__(self):
        return '<Event {}>'.format(self.id)
