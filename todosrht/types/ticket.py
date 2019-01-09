import sqlalchemy as sa
from srht.database import Base
from srht.flagtype import FlagType
from todosrht.types import TicketAccess, TicketStatus, TicketResolution

class Ticket(Base):
    __tablename__ = 'ticket'
    __table_args__ = (
        sa.UniqueConstraint('tracker_id', 'scoped_id',
            name="uq_ticket_tracker_id_scoped_id"),
    )
    id = sa.Column(sa.Integer, primary_key=True)
    created = sa.Column(sa.DateTime, nullable=False)
    updated = sa.Column(sa.DateTime, nullable=False)

    tracker_id = sa.Column(sa.Integer,
            sa.ForeignKey("tracker.id", ondelete="CASCADE"),
            nullable=False)
    tracker = sa.orm.relationship("Tracker",
            backref=sa.orm.backref("tickets", cascade="all, delete-orphan"))

    scoped_id = sa.Column(sa.Integer, nullable=False, index=True)

    dupe_of_id = sa.Column(sa.Integer,
            sa.ForeignKey("ticket.id", ondelete="SET NULL"))
    dupe_of = sa.orm.relationship("Ticket",
            backref=sa.orm.backref("dupes"),
            remote_side=[id])

    submitter_id = sa.Column(sa.Integer,
            sa.ForeignKey("user.id"), nullable=False)
    submitter = sa.orm.relationship("User",
            backref=sa.orm.backref("submitted", cascade="all, delete-orphan"))

    title = sa.Column(sa.Unicode(2048), nullable=False)
    description = sa.Column(sa.Unicode(16384))

    status = sa.Column(FlagType(TicketStatus),
            nullable=False,
            default=TicketStatus.reported)

    resolution = sa.Column(FlagType(TicketResolution),
            nullable=False,
            default=TicketResolution.unresolved)

    user_perms = sa.Column(FlagType(TicketAccess), nullable=True)
    """Permissions given to any logged in user"""

    submitter_perms = sa.Column(FlagType(TicketAccess), nullable=True)
    """Permissions granted to submitters for their own tickets"""

    committer_perms = sa.Column(FlagType(TicketAccess), nullable=True)
    """Permissions granted to people who have authored commits in the linked git repo"""

    anonymous_perms = sa.Column(FlagType(TicketAccess), nullable=True)
    """Permissions granted to anonymous (non-logged in) users"""

    view_list = sa.orm.relationship("TicketSeen")
    labels = sa.orm.relationship("Label", secondary="ticket_label")

    assigned_users = sa.orm.relationship("User",
        secondary="ticket_assignee",
        foreign_keys="[TicketAssignee.ticket_id,TicketAssignee.assignee_id]")
