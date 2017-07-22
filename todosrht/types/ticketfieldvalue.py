import sqlalchemy as sa
from srht.database import Base

class TicketFieldValue(Base):
    """Associates a ticket field with its values for a given ticket"""
    __tablename__ = 'ticket_field_value'
    id = sa.Column(sa.Integer, primary_key=True)
    created = sa.Column(sa.DateTime, nullable=False)
    updated = sa.Column(sa.DateTime, nullable=False)
    ticket_id = sa.Column(sa.Integer, sa.ForeignKey("ticket.id"))
    """
    Note: this can be None if the ticket was edited; we keep the row around for
    the audit log and keep the association via the audit log table
    """
    ticket = sa.orm.relationship("Ticket", backref=sa.orm.backref("fields"))
    ticket_field_id = sa.Column(sa.Integer,
            sa.ForeignKey("ticket_field.id"),
            nullable=False)
    ticket_field = sa.orm.relationship("TicketField")
    string_value = sa.Column(sa.Unicode(16384))
