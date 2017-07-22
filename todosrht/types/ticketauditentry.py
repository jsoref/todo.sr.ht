import sqlalchemy as sa
import sqlalchemy_utils as sau
from todosrht.types import FlagType, TicketAccess
from srht.database import Base
from enum import Enum

class AuditFieldType(Enum):
    """Describes what kind of field was updated in an audit log event"""
    name = "name"
    permissions = "permissions"
    tracker = "tracker"
    custom_field = "custom_field"
    custom_event = "custom_event"

class PermissionsTarget(Enum):
    """Describes the target of an update to ticket permissions"""
    anonymous = "anonymous"
    logged_in = "logged_in"
    submitted = "submitter"
    committer = "committer"
    user = "user"
    """A specific named user"""

class TicketAuditEntry(Base):
    """
    Records an event that has occured to a ticket. The field_type tells you
    what kind of field was affected, which is used to disambiguate the affected
    columns in the database.
    
    AuditFieldType.name is used when the ticket is renamed. old_name and
    new_name are valid for these events.

    AuditFieldType.permissions is used permissions are changed. old_permissions
    and new_permissions are valid for these events, as well as
    permissions_target, which describes what kind of user was affected by the
    change. If permissions_target == PermissionsTarget.user, a specific user's
    permissions were edited and permissions_user is valid.

    AuditFieldType.tracker is used when a ticket is moved between trackers.
    old_tracker and new_tracker are valid for this event.

    AuditFieldType.custom_field is when a custom field is edited.
    old_custom_value and new_custom_value are valid for this event.

    AuditFieldType.custom_event is used for events submitted through the API
    (i.e. build status updates). oauth_client and custom_text are valid for
    this event.
    """
    __tablename__ = 'ticket_audit_entry'
    id = sa.Column(sa.Integer, primary_key=True)
    created = sa.Column(sa.DateTime, nullable=False)
    ticket_id = sa.Column(sa.Integer, sa.ForeignKey("ticket.id"), nullable=False)
    ticket = sa.orm.relationship("Ticket",
            backref=sa.orm.backref("audit_log"))
    field_type = sa.Column(sau.ChoiceType(AuditFieldType), nullable=False)
    user_id = sa.Column(sa.Integer, sa.ForeignKey("user.id"), nullable=False)
    user = sa.orm.relationship("User",
            foreign_keys=[user_id])
    """The user who executed the change"""
    ticket_field_id = sa.Column(sa.Integer, sa.ForeignKey("ticket_field.id"))
    ticket_field = sa.orm.relationship("TicketField")
    #oauth_client_id = sa.Column(sa.Integer, sa.ForeignKey("oauth_client.id"))
    #oauth_client = sa.orm.relationship("OAuthClient")

    custom_text = sa.Column(sa.Unicode(4096))
    """Markdown, typically used for custom events submitted via API"""

    old_name = sa.Column(sa.Unicode(2048))
    new_name = sa.Column(sa.Unicode(2048))

    old_permissions = sa.Column(FlagType(TicketAccess))
    new_permissions = sa.Column(FlagType(TicketAccess))
    permissions_target = sa.Column(sau.ChoiceType(PermissionsTarget))
    permissions_user_id = sa.Column(sa.Integer, sa.ForeignKey("user.id"))
    permissions_user = sa.orm.relationship("User",
            foreign_keys=[permissions_user_id])

    old_tracker_id = sa.Column(sa.Integer,
            sa.ForeignKey("tracker.id"))
    old_tracker = sa.orm.relationship("Tracker",
            foreign_keys=[old_tracker_id])
    new_tracker_id = sa.Column(sa.Integer,
        sa.ForeignKey("tracker.id"))
    new_tracker = sa.orm.relationship("Tracker",
            foreign_keys=[new_tracker_id])

    old_custom_value_id = sa.Column(sa.Integer,
            sa.ForeignKey("ticket_field_value.id"))
    old_custom_value = sa.orm.relationship("TicketFieldValue",
             foreign_keys=[old_custom_value_id])

    new_custom_value_id = sa.Column(sa.Integer,
            sa.ForeignKey("ticket_field_value.id"))
    new_custom_value = sa.orm.relationship("TicketFieldValue",
            foreign_keys=[new_custom_value_id])
