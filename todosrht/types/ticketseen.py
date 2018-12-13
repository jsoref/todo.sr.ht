import sqlalchemy as sa
import sqlalchemy_utils as sau
from srht.database import Base
from datetime import datetime

class TicketSeen(Base):
    """Stores the last time a user viewed this ticket. Calculates if comments have been seen."""
    __tablename__ = 'ticket_seen'
    user_id = sa.Column(sa.Integer,
            sa.ForeignKey('user.id'),
            primary_key=True)
    user = sa.orm.relationship("User")

    ticket_id = sa.Column(sa.Integer,
            sa.ForeignKey('ticket.id', ondelete="CASCADE"),
            primary_key=True)
    ticket = sa.orm.relationship("Ticket", lazy="joined")

    last_view = sa.Column(sa.DateTime,
            nullable=False,
            server_default=sa.sql.func.now())


    def update(self):
        self.last_view = datetime.utcnow()
