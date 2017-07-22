import sqlalchemy as sa
from srht.database import Base

class TicketComment(Base):
    __tablename__ = "ticket_comment"
    id = sa.Column(sa.Integer, primary_key=True)
    created = sa.Column(sa.DateTime, nullable=False)
    updated = sa.Column(sa.DateTime, nullable=False)

    ticket_id = sa.Column(sa.Integer, sa.ForeignKey("ticket.id"), nullable=False)
    ticket = sa.orm.relationship("Ticket", backref=sa.orm.backref("fields"))

    user_id = sa.Column(sa.Integer, sa.ForeignKey("user.id"), nullable=False)
    user = sa.orm.relationship("User", backref=sa.orm.backref("comments"))

    text = sa.Column(sa.Unicode(16384), nullable=False)
    """Markdown"""
    visible = sa.Column(sa.Boolean, nullable=False, default=True)
    """Deleted comments stay in the system, but are removed from the listing"""
