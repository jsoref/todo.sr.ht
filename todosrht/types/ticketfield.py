import sqlalchemy as sa
import sqlalchemy_utils as sau
from srht.database import Base
from todosrht.types import FlagType, TicketAccess
from enum import Enum

class TicketFieldType(Enum):
    string = "string"
    """A single line of text"""
    multiline = "multiline"
    """Multiple lines of text"""
    markdown = "markdown"
    """Markdown text"""
    # TODO: option, multioption, boolean
    user_agent = "user_agent"
    """Value of User-Agent header when ticket is submitted"""
    # TODO: decoded user agent fields
    # TODO: user, user_list, git_tag, git_repo

class TicketField(Base):
    """
    Represents a field given to the user to fill out. All tickets have a few
    fields like name and submitter that cannot be changed.
    """
    __tablename__ = 'ticket_field'
    id = sa.Column(sa.Integer, primary_key=True)
    created = sa.Column(sa.DateTime, nullable=False)
    updated = sa.Column(sa.DateTime, nullable=False)
    tracker_id = sa.Column(sa.Integer, sa.ForeignKey("tracker.id"), nullable=False)
    tracker = sa.orm.relationship("Tracker", backref=sa.orm.backref("fields"))
    label = sa.Column(sa.Unicode(1024))
    field_type = sa.Column(sau.ChoiceType(TicketFieldType), nullable=False)
    order = sa.Column(sa.Integer, nullable=False, default=0)
    requried = sa.Column(sa.Boolean, nullable=False, default=False)
    default_value = sa.Column(sa.Unicode(16384))
    default_perms = sa.Column(FlagType(TicketAccess),
            nullable=False,
            default=TicketAccess.edit)
    """Users with this level of access to the ticket can edit this field"""
