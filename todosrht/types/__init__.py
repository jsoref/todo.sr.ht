from srht.database import Base
from srht.oauth import ExternalUserMixin
from srht.oauth import ExternalOAuthTokenMixin
import sqlalchemy as sa

class User(Base, ExternalUserMixin):
    notify_self = sa.Column(sa.Boolean, nullable=False, server_default="FALSE")

class OAuthToken(Base, ExternalOAuthTokenMixin):
    pass

from todosrht.types.ticketaccess import TicketAccess
from todosrht.types.ticketstatus import TicketStatus, TicketResolution
from todosrht.types.ticketstatus import TicketAuthenticity

from todosrht.types.event import Event, EventType, EventNotification
from todosrht.types.label import Label, TicketLabel
from todosrht.types.participant import Participant, ParticipantType
from todosrht.types.ticket import Ticket
from todosrht.types.ticketassignee import TicketAssignee
from todosrht.types.ticketcomment import TicketComment
from todosrht.types.ticketseen import TicketSeen
from todosrht.types.ticketsubscription import TicketSubscription
from todosrht.types.tracker import Tracker, Visibility
from todosrht.types.useraccess import UserAccess
