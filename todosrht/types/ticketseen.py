import sqlalchemy as sa
import sqlalchemy_utils as sau
from srht.database import Base

class TicketSeen(Base):
    """Stores the last time a user viewed this ticket. Calculates if comments have been seen."""
    __tablename__ = 'ticket_seen'
    user_id = sa.Column(sa.Integer, sa.ForeignKey('user.id'), primary_key=True)
    ticket_id = sa.Column(sa.Integer, sa.ForeignKey('ticket.id'), primary_key=True)
    last_view = sa.Column(sa.DateTime, nullable=False, server_default=sa.sql.func.now())

    user = sa.orm.relationship("User")
    ticket = sa.orm.relationship("Ticket")

    def update(self):
        self.last_view = sa.sql.func.now()
