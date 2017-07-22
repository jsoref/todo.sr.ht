import sqlalchemy as sa
from srht.database import Base
from todosrht.types import TicketAccess, FlagType

class Ticket(Base):
    """
    Represents a ticket filed in the system. The default permissions are
    inherited from the tracker configuration, but may be edited to i.e.

    - Give an arbitrary edit/view/whatever access
    - Remove a specific user's permission to edit
    - Allow the public to comment on an otherwise uncommentable issue
    - Lock an issue from further discussion from non-contributors
    - etc
    """
    __tablename__ = 'ticket'
    id = sa.Column(sa.Integer, primary_key=True)
    created = sa.Column(sa.DateTime, nullable=False)
    updated = sa.Column(sa.DateTime, nullable=False)
    ticket_id = sa.Column(sa.Integer, index=True)
    """The ID specific to this tracker, appears in URLs etc"""
    name = sa.Column(sa.Unicode(2048), nullable=False)

    tracker_id = sa.Column(sa.Integer, sa.ForeignKey("tracker.id"), nullable=False)
    tracker = sa.orm.relationship("Tracker", backref=sa.orm.backref("tickets"))

    submitter_id = sa.Column(sa.Integer, sa.ForeignKey("user.id"), nullable=False)
    submitter = sa.orm.relationship("User", backref=sa.orm.backref("tickets"))

    default_user_perms = sa.Column(FlagType(TicketAccess), nullable=False)
    """Permissions given to any logged in user"""

    default_submitter_perms = sa.Column(FlagType(TicketAccess), nullable=False)
    """Permissions granted to the ticket submitter"""

    default_committer_perms = sa.Column(FlagType(TicketAccess), nullable=False)
    """Permissions granted to people who have authored commits in the linked git repo"""

    default_anonymous_perms = sa.Column(FlagType(TicketAccess), nullable=False)
    """Permissions granted to anonymous (non-logged in) users"""
