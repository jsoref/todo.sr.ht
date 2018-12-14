from collections import namedtuple
from datetime import datetime
from srht.config import cfg
from srht.database import db
from todosrht.email import notify
from todosrht.types import Event, EventType, EventNotification
from todosrht.types import TicketComment, TicketStatus, TicketSubscription
from todosrht.types import TicketSeen, TicketAssignee
from todosrht.urls import ticket_url
from sqlalchemy import func

smtp_user = cfg("mail", "smtp-user", default=None)
smtp_from = cfg("mail", "smtp-from", default=None)
notify_from = cfg("todo.sr.ht", "notify-from", default=smtp_from)

StatusChange = namedtuple("StatusChange", [
    "old_status",
    "new_status",
    "old_resolution",
    "new_resolution",
])

def _create_comment(ticket, user, text):
    comment = TicketComment()
    comment.text = text
    # TODO: anonymous comments (when configured appropriately)
    comment.submitter_id = user.id
    comment.ticket_id = ticket.id

    db.session.add(comment)
    db.session.flush()
    return comment

def _create_comment_event(ticket, user, comment, status_change):
    event = Event()
    event.event_type = 0
    event.user_id = user.id
    event.ticket_id = ticket.id

    if comment:
        event.event_type |= EventType.comment
        event.comment_id = comment.id

    if status_change:
        event.event_type |= EventType.status_change
        event.old_status = status_change.old_status
        event.old_resolution = status_change.old_resolution
        event.new_status = status_change.new_status
        event.new_resolution = status_change.new_resolution

    db.session.add(event)
    db.session.flush()
    return event

def _create_event_notification(user, event):
    notification = EventNotification()
    notification.user_id = user.id
    notification.event_id = event.id
    db.session.add(notification)
    return notification

def _send_comment_notification(subscription, ticket, user, comment, resolution):
    subject = "Re: {}/{}/#{}: {}".format(
        ticket.tracker.owner.canonical_name(),
        ticket.tracker.name,
        ticket.scoped_id,
        ticket.title)

    headers = {
        "From": "~{} <{}>".format(user.username, notify_from),
        "Sender": smtp_user,
    }

    url = ticket_url(ticket, comment=comment).replace("%7E", "~")  # hack

    notify(subscription, "ticket_comment", subject,
        headers=headers,
        ticket=ticket,
        comment=comment,
        resolution=resolution.name if resolution else None,
        ticket_url=url)

def _change_ticket_status(ticket, resolve, resolution, reopen):
    if not (resolve or reopen):
        return None

    old_status = ticket.status
    old_resolution = ticket.resolution

    if resolve:
        ticket.status = TicketStatus.resolved
        ticket.resolution = resolution

    if reopen:
        ticket.status = TicketStatus.reported

    return StatusChange(
        old_status, ticket.status, old_resolution, ticket.resolution)

def _send_comment_notifications(user, ticket, event, comment, resolution):
    # Find subscribers, eliminate duplicates
    subscriptions = {sub.user: sub
        for sub in ticket.tracker.subscriptions + ticket.subscriptions}

    # Subscribe commenter if not already subscribed
    if user not in subscriptions:
        subscription = TicketSubscription()
        subscription.ticket_id = ticket.id
        subscription.user_id = user.id
        db.session.add(subscription)
        subscriptions[user] = subscription

    for subscriber, subscription in subscriptions.items():
        _create_event_notification(subscriber, event)
        if subscriber != user:
            _send_comment_notification(
                subscription, ticket, user, comment, resolution)

def add_comment(user, ticket,
        text=None, resolve=False, resolution=None, reopen=False):
    """
    Comment on a ticket, optionally resolve or reopen the ticket.
    """
    # TODO better error handling
    assert text or resolve or reopen
    assert not (resolve and reopen)
    if resolve:
        assert resolution is not None

    comment = _create_comment(ticket, user, text) if text else None
    status_change = _change_ticket_status(ticket, resolve, resolution, reopen)
    event = _create_comment_event(ticket, user, comment, status_change)
    _send_comment_notifications(user, ticket, event, comment, resolution)

    ticket.updated = datetime.utcnow()
    ticket.tracker.updated = datetime.utcnow()
    db.session.commit()

    return comment

def mark_seen(ticket, user):
    """Mark the ticket as seen by user."""
    seen = TicketSeen.query.filter_by(user=user, ticket=ticket).one_or_none()
    if seen:
        seen.update()  # Updates last_view time
    else:
        seen = TicketSeen(user_id=user.id, ticket_id=ticket.id)
        db.session.add(seen)

    return seen

def assign(ticket, assignee, assigner):
    role = ""  # Role is not yet implemented

    ticket_assignee = TicketAssignee.query.filter_by(
        ticket=ticket, assignee=assignee).one_or_none()

    if not ticket_assignee:
        ticket_assignee = TicketAssignee(
            ticket=ticket,
            assignee=assignee,
            assigner=assigner,
            role=role,
        )
        db.session.add(ticket_assignee)

    event = Event()
    event.event_type = EventType.assigned_user
    event.user_id = assigner.id
    event.ticket_id = ticket.id
    event.assigned_user_id = assignee.id
    db.session.add(event)

    return ticket_assignee

def unassign(ticket, assignee, assigner):
    TicketAssignee.query.filter_by(ticket=ticket, assignee=assignee).delete()

    event = Event()
    event.event_type = EventType.unassigned_user
    event.user_id = assigner.id
    event.ticket_id = ticket.id
    event.assigned_user_id = assignee.id
    db.session.add(event)

def get_last_seen_times(user, tickets):
    """Fetches last times the user has seen each of the given tickets."""
    return dict(db.session.query(TicketSeen.ticket_id, TicketSeen.last_view)
        .filter(TicketSeen.ticket_id.in_([t.id for t in tickets]))
        .filter(TicketSeen.user == user))

def get_comment_counts(tickets):
    """Returns comment counts indexed by ticket id."""
    col = TicketComment.ticket_id
    return dict(db.session
        .query(col, func.count(col))
        .filter(col.in_([t.id for t in tickets]))
        .group_by(col))
