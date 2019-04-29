from flask_login import current_user
from todosrht.types import User, Tracker, Ticket
from todosrht.types import TicketAccess

def get_access(tracker, ticket, user=None):
    if user is None:
        user = current_user
    # TODO: flesh out
    if user and user.id == tracker.owner_id:
        return TicketAccess.all
    elif user:
        if ticket and user.id == ticket.submitter_id:
            return ticket.submitter_perms or tracker.default_submitter_perms
        return tracker.default_user_perms

    if ticket and ticket.anonymous_perms:
        return ticket.anonymous_perms
    return tracker.default_anonymous_perms

def get_owner(owner):
    pass

def get_tracker(owner, name, with_for_update=False, user=None):
    if not owner:
        return None, None

    if owner.startswith("~"):
        owner = owner[1:]

    owner = User.query.filter(User.username == owner).one_or_none()
    if not owner:
        return None, None
    tracker = (Tracker.query
        .filter(Tracker.owner_id == owner.id)
        .filter(Tracker.name == name.lower()))
    if with_for_update:
        tracker = tracker.with_for_update()
    tracker = tracker.one_or_none()
    if not tracker:
        return None, None
    access = get_access(tracker, None, user=user)
    if access:
        return tracker, access

    # TODO: org trackers
    return None, None

def get_ticket(tracker, ticket_id, user=None):
    ticket = (Ticket.query
            .filter(Ticket.scoped_id == ticket_id)
            .filter(Ticket.tracker_id == tracker.id)).one_or_none()
    if not ticket:
        return None, None
    access = get_access(tracker, ticket, user=user)
    if not TicketAccess.browse in access:
        return None, None
    return ticket, access
