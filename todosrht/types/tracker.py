import re
import sqlalchemy as sa
import sqlalchemy_utils as sau
import string
from enum import Enum
from srht.database import Base
from srht.flagtype import FlagType
from srht.validation import Validation
from todosrht.types import TicketAccess, TicketStatus, TicketResolution

name_re = re.compile(r"^[A-Za-z0-9._-]+$")

class Visibility(Enum):
    PUBLIC = 'PUBLIC'
    UNLISTED = 'UNLISTED'
    PRIVATE = 'PRIVATE'

class Tracker(Base):
    __tablename__ = 'tracker'
    __table_args__ = (
        sa.UniqueConstraint("owner_id", "name",
            name="tracker_owner_id_name_unique"),
    )

    id = sa.Column(sa.Integer, primary_key=True)
    owner_id = sa.Column(sa.Integer, sa.ForeignKey("user.id"), nullable=False)
    owner = sa.orm.relationship("User", backref=sa.orm.backref("owned_trackers"))
    created = sa.Column(sa.DateTime, nullable=False)
    updated = sa.Column(sa.DateTime, nullable=False)
    visibility = sa.Column(sau.ChoiceType(Visibility), nullable=False)
    name = sa.Column(sa.Unicode(1024))
    """
    May include slashes to serve as categories (nesting is supported,
    builds.sr.ht style)
    """
    next_ticket_id = sa.Column(sa.Integer, nullable=False, server_default='1')

    description = sa.Column(sa.Unicode(8192))
    """Markdown"""

    default_access = sa.Column(FlagType(TicketAccess),
            nullable=False,
            server_default=str(TicketAccess.browse + TicketAccess.submit + TicketAccess.comment))

    import_in_progress = sa.Column(sa.Boolean,
            nullable=False, server_default='f')

    def ref(self):
        return "{}/{}".format(
            self.owner.canonical_name,
            self.name)

    def __repr__(self):
        return '<Tracker {} {}>'.format(self.id, self.name)

    def to_dict(self, short=False):
        def permissions(w):
            if isinstance(w, int):
                w = TicketAccess(w)
            return [p.name for p in TicketAccess
                    if p in w and p not in [TicketAccess.none, TicketAccess.all]]
        return {
            "id": self.id,
            "owner": self.owner.to_dict(short=True),
            "created": self.created,
            "updated": self.updated,
            "name": self.name,
            **({
                "description": self.description,
                "default_access": permissions(self.default_access),
                "visibility": self.visibility,
            } if not short else {})
        }
