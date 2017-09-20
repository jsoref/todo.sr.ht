import sqlalchemy as sa
from srht.database import Base
from srht.flagtype import FlagType
from todosrht.types import TicketAccess, TicketStatus, TicketResolution

class Tracker(Base):
    __tablename__ = 'tracker'
    id = sa.Column(sa.Integer, primary_key=True)
    owner_id = sa.Column(sa.Integer, sa.ForeignKey("user.id"), nullable=False)
    owner = sa.orm.relationship("User", backref=sa.orm.backref("owned_trackers"))
    created = sa.Column(sa.DateTime, nullable=False)
    updated = sa.Column(sa.DateTime, nullable=False)
    name = sa.Column(sa.Unicode(1024))
    """
    May include slashes to serve as categories (nesting is supported,
    builds.sr.ht style)
    """
    next_ticket_id = sa.Column(sa.Integer, nullable=False, default=1)

    description = sa.Column(sa.Unicode(8192))
    """Markdown"""

    min_desc_length = sa.Column(sa.Integer, nullable=False, default=0)

    enable_ticket_status = sa.Column(FlagType(TicketStatus),
            nullable=False,
            default=TicketStatus.resolved)

    enable_ticket_resolution = sa.Column(FlagType(TicketStatus),
            nullable=False,
            default=TicketResolution.fixed | TicketResolution.duplicate)

    default_user_perms = sa.Column(FlagType(TicketAccess),
            nullable=False,
            default=TicketAccess.browse + TicketAccess.submit + TicketAccess.comment)
    """Permissions given to any logged in user"""

    default_submitter_perms = sa.Column(FlagType(TicketAccess),
            nullable=False,
            default=TicketAccess.browse + TicketAccess.edit + TicketAccess.comment)
    """Permissions granted to submitters for their own tickets"""

    default_committer_perms = sa.Column(FlagType(TicketAccess),
            nullable=False,
            default=TicketAccess.browse + TicketAccess.submit + TicketAccess.comment)
    """Permissions granted to people who have authored commits in the linked git repo"""

    default_anonymous_perms = sa.Column(FlagType(TicketAccess),
            nullable=False,
            default=TicketAccess.browse)
    """Permissions granted to anonymous (non-logged in) users"""

    def __repr__(self):
        return '<Tracker {} {}>'.format(self.id, self.name)
