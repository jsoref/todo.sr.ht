import sqlalchemy as sa
from srht.database import Base

class TicketAssignee(Base):
    __tablename__ = 'ticket_assignee'
    id = sa.Column(sa.Integer, primary_key=True)
    created = sa.Column(sa.DateTime, nullable=False)
    updated = sa.Column(sa.DateTime, nullable=False)

    ticket_id = sa.Column(sa.Integer,
            sa.ForeignKey("ticket.id", ondelete="CASCADE"),
            nullable=False)
    ticket = sa.orm.relationship("Ticket",
            backref=sa.orm.backref("assignees", cascade="all, delete-orphan"))

    assignee_id = sa.Column(sa.Integer,
            sa.ForeignKey("user.id"),
            nullable=False)
    assignee = sa.orm.relationship("User", foreign_keys=[assignee_id])

    assigner_id = sa.Column(sa.Integer,
            sa.ForeignKey("user.id"),
            nullable=False)
    assigner = sa.orm.relationship("User", foreign_keys=[assigner_id])

    role = sa.Column(sa.Unicode(256))
