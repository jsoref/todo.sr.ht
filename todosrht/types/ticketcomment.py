import sqlalchemy as sa
from srht.database import Base
from srht.flagtype import FlagType
from todosrht.types import TicketAccess, TicketStatus, TicketResolution

class TicketComment(Base):
    __tablename__ = 'ticket_comment'
    id = sa.Column(sa.Integer, primary_key=True)
    created = sa.Column(sa.DateTime, nullable=False)
    updated = sa.Column(sa.DateTime, nullable=False)

    submitter_id = sa.Column(sa.Integer, sa.ForeignKey("user.id"), nullable=False)
    submitter = sa.orm.relationship("User")

    ticket_id = sa.Column(sa.Integer, sa.ForeignKey("ticket.id"), nullable=False)
    ticket = sa.orm.relationship("Ticket", backref=sa.orm.backref("comments"))

    text = sa.Column(sa.Unicode(16384))
