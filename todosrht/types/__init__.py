from srht.database import Base
from srht.oauth import ExternalUserMixin
from srht.oauth import ExternalOAuthTokenMixin

class User(Base, ExternalUserMixin):
    pass

class OAuthToken(Base, ExternalOAuthTokenMixin):
    pass

from todosrht.types.ticketaccess import TicketAccess
from todosrht.types.ticketstatus import TicketStatus, TicketResolution
from todosrht.types.tracker import Tracker
from todosrht.types.ticketseen import TicketSeen
from todosrht.types.ticket import Ticket
from todosrht.types.ticketsubscription import TicketSubscription
from todosrht.types.ticketcomment import TicketComment
from todosrht.types.ticketassignee import TicketAssignee
from todosrht.types.event import Event, EventType, EventNotification
from todosrht.types.label import Label, TicketLabel
