import sqlalchemy as sa
from srht.database import Base
from srht.flagtype import FlagType
from todosrht.types import TicketAccess, TicketStatus, TicketResolution, TicketSeen

class Ticket(Base):
    __tablename__ = 'ticket'
    id = sa.Column(sa.Integer, primary_key=True)
    created = sa.Column(sa.DateTime, nullable=False)
    updated = sa.Column(sa.DateTime, nullable=False)

    tracker_id = sa.Column(sa.Integer, sa.ForeignKey("tracker.id"), nullable=False)
    tracker = sa.orm.relationship("Tracker", backref=sa.orm.backref("tickets"))

    scoped_id = sa.Column(sa.Integer,
            nullable=False,
            index=True,
            unique=sa.UniqueConstraint('scoped_id', 'tracker_id'))

    dupe_of_id = sa.Column(sa.Integer, sa.ForeignKey("ticket.id"))
    dupe_of = sa.orm.relationship("Ticket",
            backref=sa.orm.backref("dupes"),
            remote_side=[id])

    submitter_id = sa.Column(sa.Integer, sa.ForeignKey("user.id"), nullable=False)
    submitter = sa.orm.relationship("User", backref=sa.orm.backref("submitted"))

    title = sa.Column(sa.Unicode(2048), nullable=False)
    description = sa.Column(sa.Unicode(16384))
    user_agent = sa.Column(sa.Unicode(2048))

    status = sa.Column(FlagType(TicketStatus),
            nullable=False,
            default=TicketStatus.reported)

    resolution = sa.Column(FlagType(TicketResolution),
            nullable=False,
            default=TicketStatus.resolved)

    user_perms = sa.Column(FlagType(TicketAccess), nullable=True)
    """Permissions given to any logged in user"""

    submitter_perms = sa.Column(FlagType(TicketAccess), nullable=True)
    """Permissions granted to submitters for their own tickets"""

    committer_perms = sa.Column(FlagType(TicketAccess), nullable=True)
    """Permissions granted to people who have authored commits in the linked git repo"""

    anonymous_perms = sa.Column(FlagType(TicketAccess), nullable=True)
    """Permissions granted to anonymous (non-logged in) users"""

    view_list = sa.orm.relationship("TicketSeen")
    def new_updates(self, user):
        if not user:
            return None
        seen = (TicketSeen.query
                .filter(TicketSeen.user_id == user.id,
                    TicketSeen.ticket_id == self.id)
                .one_or_none())
        if seen:
            return seen.last_view >= self.updated
        return None
