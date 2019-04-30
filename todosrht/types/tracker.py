import re
import sqlalchemy as sa
import string
from srht.database import Base
from srht.flagtype import FlagType
from todosrht.types import TicketAccess, TicketStatus, TicketResolution

name_re = re.compile(r"^([a-z][a-z0-9_.-]*?)+$")

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

    def __init__(self, user, valid):
        name = valid.require("name", friendly_name="Name")
        desc = valid.optional("description")
        if not valid.ok:
            return

        valid.expect(2 < len(name) < 256,
                "Must be between 2 and 256 characters",
                field="name")
        valid.expect(not valid.ok or name[0] in string.ascii_lowercase,
                "Must begin with a lowercase letter", field="name")
        valid.expect(not valid.ok or name_re.match(name),
                "Only lowercase alphanumeric characters or -.",
                field="name")
        valid.expect(not desc or len(desc) < 4096,
                "Must be less than 4096 characters",
                field="description")
        if not valid.ok:
            return

        tracker = (Tracker.query
                .filter(Tracker.owner_id == user.id)
                .filter(Tracker.name == name)
            ).first()
        valid.expect(not tracker,
                "A tracker by this name already exists", field="name")
        if not valid.ok:
            return

        self.owner_id = user.id
        self.name = name
        self.description = desc

    def __repr__(self):
        return '<Tracker {} {}>'.format(self.id, self.name)

    def to_dict(self):
        def permissions(w):
            return [p.name for p in TicketAccess
                    if p in w and p not in [TicketAccess.none, TicketAccess.all]]
        return {
            "id": self.id,
            "owner": self.owner.to_dict(short=True),
            "created": self.created,
            "updated": self.updated,
            "name": self.name,
            "description": self.description,
            "default_permissions": {
                "anonymous": permissions(self.default_anonymous_perms),
                "submitter": permissions(self.default_submitter_perms),
                "user": permissions(self.default_user_perms),
            },
        }

    def update(self, valid):
        desc = valid.optional("description", default=self.description)
        valid.expect(not desc or len(desc) < 4096,
                "Must be less than 4096 characters",
                field="description")
        self.description = desc
