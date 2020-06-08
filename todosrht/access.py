from srht.oauth import current_user
from todosrht.types import User, Tracker, Ticket
from todosrht.types import TicketAccess, UserAccess

def _get_permissions(tracker, ticket, name):
    """
    Return ticket permissions of given name, fall back to tracker defaults.
    """
    if ticket and getattr(ticket, f"{name}_perms"):
        return getattr(ticket, f"{name}_perms")
    return getattr(tracker, f"default_{name}_perms")

# TODO: get_access for any participant
def get_access(tracker, ticket, user=None):
    user = user or current_user

    # Anonymous
    if not user:
        return _get_permissions(tracker, ticket, "anonymous")

    # Owner
    if user.id == tracker.owner_id:
        return TicketAccess.all

    # Per-user access specified
    user_access = UserAccess.query.filter_by(tracker=tracker, user=user).first()
    if user_access:
        return user_access.permissions

    # Submitter
    if ticket and user.id == ticket.submitter.user_id:
        return _get_permissions(tracker, ticket, "submitter")

    # Any logged in user
    return _get_permissions(tracker, ticket, "user")


def get_tracker(owner, name, with_for_update=False, user=None):
    if not owner:
        return None, None

    if owner[0] == "~":
        owner = owner[1:]
        if not isinstance(owner, User):
            owner = User.query.filter(User.username == owner).one_or_none()
            if not owner:
                return None, None
        tracker = (Tracker.query
            .filter(Tracker.owner_id == owner.id)
            .filter(Tracker.name.ilike(name)))
        if with_for_update:
            tracker = tracker.with_for_update()
        tracker = tracker.one_or_none()
        if not tracker:
            return None, None
        access = get_access(tracker, None, user=user)
        if access:
            return tracker, access
    else:
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
