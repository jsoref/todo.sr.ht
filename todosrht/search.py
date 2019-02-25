from sqlalchemy import or_
from srht.search import search
from todosrht.types import Label, TicketLabel
from todosrht.types import Ticket, TicketStatus, TicketComment
from todosrht.types import User

STATUS_ALIASES = {
    "open": [
        TicketStatus.reported,
        TicketStatus.confirmed,
        TicketStatus.in_progress,
        TicketStatus.pending,
    ],
    "closed": [TicketStatus.resolved]
}

def filter_by_status(query, value):
    if value in STATUS_ALIASES:
        return query.filter(Ticket.status.in_(STATUS_ALIASES[value]))

    if hasattr(TicketStatus, value):
        return query.filter(Ticket.status == getattr(TicketStatus, value))

    return query.filter(False)

def _get_user(value, current_user):
    if not value:
        return None

    if value == "me":
        return current_user

    return User.query.filter_by(username=value.lstrip("~")).first()

def filter_by_submitter(query, value, current_user):
    user = _get_user(value, current_user)
    if user:
        return query.filter_by(submitter=user)

    return query.filter(False)

def filter_by_assignee(query, value, current_user):
    user = _get_user(value, current_user)
    if user:
        return query.filter(Ticket.assigned_users.contains(user))

    return query.filter(False)

def filter_by_label(query, value, tracker):
    label = Label.query.filter(
        Label.tracker_id == tracker.id,
        Label.name == value).first()

    if label:
        return query.filter(Ticket.labels.any(TicketLabel.label == label))

    return query.filter(False)

def filter_no(query, value, tracker):
    filterNo = {
        'assignee': Ticket.assigned_users == None,
        'label': Ticket.labels == None,
    }
    return query.filter(filterNo.get(value, False))

def apply_search(query, terms, tracker, current_user):
    if not terms:
        return query.filter(Ticket.status == TicketStatus.reported)

    return search(query, terms, [
        Ticket.description,
        Ticket.title,
        lambda v: Ticket.comments.any(TicketComment.text.ilike(f"%{v}%"))
    ], {
        "status": lambda q, v: filter_by_status(q, v),
        "submitter": lambda q, v: filter_by_submitter(q, v, current_user),
        "assigned": lambda q, v: filter_by_assignee(q, v, current_user),
        "label": lambda q, v: filter_by_label(q, v, tracker),
        "no": lambda q, v: filter_no(q, v, tracker),
    })

def find_usernames(query, limit=20):
    """Given a partial username string, returns matching usernames."""
    if not query or query == '~':
        return []

    if query.startswith("~"):
        where = User.username.startswith(query[1:], autoescape=True)
    else:
        where = User.username.contains(query, autoescape=True)

    from todosrht.app import db
    rows = (db.session
        .query(User.username)
        .filter(where)
        .order_by(User.username)
        .limit(limit))

    return [f"~{r[0]}" for r in rows]
