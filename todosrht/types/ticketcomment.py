import sqlalchemy as sa
from srht.database import Base
from srht.flagtype import FlagType
from todosrht.types import TicketAccess, TicketStatus, TicketResolution

class TicketComment(Base):
    __tablename__ = 'ticket_comment'
    id = sa.Column(sa.Integer, primary_key=True)
    created = sa.Column(sa.DateTime, nullable=False)
    updated = sa.Column(sa.DateTime, nullable=False)

    submitter_id = sa.Column(sa.Integer,
            sa.ForeignKey("participant.id"), nullable=False)
    submitter = sa.orm.relationship("Participant")

    ticket_id = sa.Column(sa.Integer,
            sa.ForeignKey("ticket.id", ondelete="CASCADE"),
            nullable=False)
    ticket = sa.orm.relationship("Ticket",
            backref=sa.orm.backref("comments", cascade="all, delete-orphan"))

    text = sa.Column(sa.Unicode(16384))

    def to_dict(self, short=False):
        return {
            "id": self.id,
            "created": self.created,
            "submitter": self.submitter.to_dict(short=True),
            "text": self.text,
            **({
                "ticket": self.ticket.to_dict(short=True),
            } if not short else {})
        }
