from flask import has_app_context, url_for
from jinja2.utils import unicode_urlencode

def tracker_url(tracker):
    return url_for("tracker.tracker_GET",
        owner=tracker.owner.canonical_name,
        name=tracker.name)

def tracker_labels_url(tracker):
    return url_for("tracker.tracker_labels_GET",
        owner=tracker.owner.canonical_name,
        name=tracker.name)

def ticket_url(ticket, comment=None):
    if has_app_context():
        ticket_url = url_for("ticket.ticket_GET",
                owner=ticket.tracker.owner.canonical_name,
                name=ticket.tracker.name,
                ticket_id=ticket.scoped_id)
    else:
        ticket_url = (f"/{ticket.tracker.owner.canonical_name}" +
            f"/{ticket.tracker.name}" +
            f"/{ticket.scoped_id}")

    if comment:
        ticket_url += "#comment-" + str(comment.id)

    return ticket_url

def ticket_edit_url(ticket):
    return url_for("ticket.ticket_edit_GET",
        owner=ticket.tracker.owner.canonical_name,
        name=ticket.tracker.name,
        ticket_id=ticket.scoped_id)

def ticket_assign_url(ticket):
    return url_for("ticket.ticket_assign",
        owner=ticket.tracker.owner.canonical_name,
        name=ticket.tracker.name,
        ticket_id=ticket.scoped_id)

def ticket_unassign_url(ticket):
    return url_for("ticket.ticket_unassign",
        owner=ticket.tracker.owner.canonical_name,
        name=ticket.tracker.name,
        ticket_id=ticket.scoped_id)

def label_search_url(label, terms=""):
    """Return the URL to the tracker page listing all tickets which have the
    label applied."""
    return "{}?search=label:&quot;{}&quot;{}".format(
        tracker_url(label.tracker),
        unicode_urlencode(label.name),
        f" {unicode_urlencode(terms)}" if terms else "")

def label_add_url(ticket):
    """Return the URL to add a label to a ticket."""
    return url_for("ticket.ticket_add_label",
            owner=ticket.tracker.owner.canonical_name,
            name=ticket.tracker.name,
            ticket_id=ticket.scoped_id)

def label_remove_url(label, ticket):
    """Return the URL to remove a label from a ticket."""
    return url_for("ticket.ticket_remove_label",
            owner=ticket.tracker.owner.canonical_name,
            name=ticket.tracker.name,
            ticket_id=ticket.scoped_id,
            label_id=label.id)

def user_url(user):
    return url_for("html.user_GET", username=user.username)
