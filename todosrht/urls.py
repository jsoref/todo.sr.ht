from flask import url_for
from jinja2.utils import unicode_urlencode

def tracker_url(tracker):
    return url_for("tracker.tracker_GET",
        owner=tracker.owner.canonical_name(),
        name=tracker.name)

def label_search_url(label):
    """Return the URL to the tracker page listing all tickets which have the
    label applied."""
    return "{}?search=label:&quot;{}&quot;".format(
        tracker_url(label.tracker),
        unicode_urlencode(label.name))

def label_remove_url(label, ticket):
    """Return the URL to remove a label from an ticket."""
    return url_for("ticket.ticket_remove_label",
            owner=ticket.tracker.owner.canonical_name(),
            name=ticket.tracker.name,
            ticket_id=ticket.scoped_id,
            label_id=label.id,)
