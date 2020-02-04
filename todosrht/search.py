from sqlalchemy import or_
from srht import search
from todosrht.types import Label, Ticket, TicketStatus, TicketComment
from todosrht.types import Participant, User


STATUS_ALIASES = {
    "open": [
        TicketStatus.reported,
        TicketStatus.confirmed,
        TicketStatus.in_progress,
        TicketStatus.pending,
    ],
    "closed": [TicketStatus.resolved]
}

def status_filter(value):
    if value == "any":
        return True

    if value in STATUS_ALIASES:
        return Ticket.status.in_(STATUS_ALIASES[value])

    status = getattr(TicketStatus, value, None)
    if status is None:
        raise ValueError(f"Invalid status: '{value}'")

    return Ticket.status == status

def submitter_filter(value, current_user):
    if value == "me":
        return Ticket.submitter == current_user
    else:
        return Ticket.submitter.has(
            Participant.user.has(User.username.ilike(value.lstrip("~")))
        )

def asignee_filter(value, current_user):
    if value == "me":
        return Ticket.assigned_users.contains(current_user)
    else:
        return Ticket.assigned_users.any(
            User.username.ilike(value.lstrip("~"))
        )

def label_filter(value):
    return Ticket.labels.any(Label.name == value)

def no_filter(value):
    if value == "assignee":
        return Ticket.assigned_users == None

    if value == "label":
        return Ticket.labels == None

    raise ValueError(f"Invalid search term: 'no:{value}'")

def default_filter(value):
    return or_(
        Ticket.description.ilike(f"%{value}%"),
        Ticket.title.ilike(f"%{value}%"),
        Ticket.comments.any(TicketComment.text.ilike(f"%{value}%"))
    )

def apply_search(query, search_string, current_user):
    terms = list(search.parse_terms(search_string))

    # If search does not include a status filter, show open tickets
    if not any([term.key == "status" for term in terms]):
        terms.append(search.Term("status", "open", False))

    return search.apply_terms(query, terms, default_filter, key_fns={
        "status": status_filter,
        "submitter": lambda v: submitter_filter(v, current_user),
        "assigned": lambda v: asignee_filter(v, current_user),
        "label": label_filter,
        "no": no_filter,
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
