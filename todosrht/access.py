from srht.oauth import current_user
from todosrht.types import User, Tracker, Ticket, Visibility
from todosrht.types import TicketAccess, UserAccess, Participant

# TODO: get_access for any participant
def get_access(tracker, ticket, user=None):
    user = user or current_user

    # Anonymous
    if not user:
        if tracker.visibility == Visibility.PRIVATE:
            return TicketAccess.none
        return tracker.default_access

    # Owner
    if user.id == tracker.owner_id:
        return TicketAccess.all

    # ACL entry?
    user_access = UserAccess.query.filter_by(tracker=tracker, user=user).first()
    if user_access:
        return user_access.permissions

    if tracker.visibility == Visibility.PRIVATE:
        return TicketAccess.none
    return tracker.default_access


def get_tracker(owner, name, with_for_update=False, user=None):
    if not owner:
        return None, None

    if not isinstance(owner, User):
        if owner[0] == "~":
            owner = owner[1:]
            if not isinstance(owner, User):
                owner = User.query.filter(User.username == owner).one_or_none()
                if not owner:
                    return None, None
        else:
            # TODO: org trackers
            return None, None
    tracker = (Tracker.query
        .filter(Tracker.owner_id == owner.id)
        .filter(Tracker.name.ilike(name.replace('_', '\\_'))))
    if with_for_update:
        tracker = tracker.with_for_update()
    tracker = tracker.one_or_none()
    if not tracker:
        return None, None
    return tracker, get_access(tracker, None, user=user)

def get_ticket(tracker, ticket_id, user=None):
    user = user or current_user
    ticket = (Ticket.query
            .join(Participant)
            .filter(Ticket.scoped_id == ticket_id)
            .filter(Ticket.tracker_id == tracker.id)).one_or_none()
    if not ticket:
        return None, None
    access = get_access(tracker, ticket, user=user)
    if user and user.id == ticket.submitter.user_id:
        access |= TicketAccess.browse
    if not TicketAccess.browse in access:
        return None, None
    return ticket, access
