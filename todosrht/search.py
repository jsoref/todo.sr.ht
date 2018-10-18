import re
from sqlalchemy import or_
from todosrht.types import Label, TicketLabel
from todosrht.types import Ticket, TicketStatus
from todosrht.types import User

# Property with a quoted value, e.g.: label:"help wanted"
TERM_PROPERTY_QUOTED = re.compile(r"(\w+):\"(.+?)\"")

# Property with an unquoted value, e.g.: status:closed
TERM_PROPERTY_UNQUOTED = re.compile(r"(\w+):(\w+)")

# Quoted search string, e.g.: "some thing"
TERM_SEARCH_QUOTED = re.compile(r"\"(.+?)\"")

# Unquoted search string, e.g.: foo
TERM_SEARCH_UNQUOTED = re.compile(r"(\w+)")

TERM_PATTERNS = (
    TERM_PROPERTY_QUOTED,
    TERM_PROPERTY_UNQUOTED,
    TERM_SEARCH_QUOTED,
    TERM_SEARCH_UNQUOTED
)

def _process_term_match(match):
    """Parses a matched search term.

    Returns (prop, value) for properties, and (None, value) for other terms.
    """
    groups = match.groups()
    if len(groups) == 2:
        prop, term = groups
        return prop.strip().lower(), term.strip()

    return None, groups[0].strip()

def find_search_terms(search):
    """Extracts search terms from a search string"""
    for pattern in TERM_PATTERNS:
        m = re.search(pattern, search)
        while m:
            yield _process_term_match(m)
            # Remove matched term from search string
            start, end = m.span()
            search = search[:start] + search[end:]
            m = re.search(pattern, search)

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

def filter_by_submitter(query, value, current_user):
    if value == "me":
        return query.filter(Ticket.submitter_id == current_user.id)

    user = User.query.filter(User.username == value).first()
    if user:
        return query.filter(Ticket.submitter_id == user.id)

    return query.filter(False)

def filter_by_label(query, value, tracker):
    label = Label.query.filter(
        Label.tracker_id == tracker.id,
        Label.name == value).first()

    if label:
        return query.filter(Ticket.labels.any(TicketLabel.label == label))

    return query.filter(False)

def apply_search(query, search, tracker, current_user):
    terms = find_search_terms(search)
    for prop, value in terms:
        if prop == "status":
            query = filter_by_status(query, value)
            continue

        if prop == "submitter":
            query = filter_by_submitter(query, value, current_user)
            continue

        if prop == "label":
            query = filter_by_label(query, value, tracker)
            continue

        query = query.filter(or_(
            Ticket.description.ilike("%" + value + "%"),
            Ticket.title.ilike("%" + value + "%")))

    return query
