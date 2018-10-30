from datetime import datetime
from flask import url_for
from srht.config import cfg
from srht.database import db
from todosrht.email import notify
from todosrht.types import Event, EventType, EventNotification
from todosrht.types import TicketComment, TicketStatus, TicketSubscription

smtp_user = cfg("mail", "smtp-user", default=None)
smtp_from = cfg("mail", "smtp-from", default=None)
notify_from = cfg("todo.sr.ht", "notify-from", default=smtp_from)


def add_comment(user, ticket,
        text=None, resolve=False, resolution=None, reopen=False):

    assert text or resolve or reopen

    tracker = ticket.tracker

    if text:
        comment = TicketComment()
        comment.text = text
        # TODO: anonymous comments (when configured appropriately)
        comment.submitter_id = user.id
        comment.ticket_id = ticket.id
        db.session.add(comment)
        ticket.updated = comment.created
    else:
        comment = None

    old_status = ticket.status
    old_resolution = ticket.resolution

    if resolution:
        ticket.status = TicketStatus.resolved
        ticket.resolution = resolution

    if reopen:
        ticket.status = TicketStatus.reported

    tracker.updated = datetime.utcnow()
    db.session.flush()

    subscribed = False

    ticket_url = url_for("ticket.ticket_GET",
            owner=tracker.owner.canonical_name(),
            name=tracker.name,
            ticket_id=ticket.scoped_id)
    if comment:
        ticket_url += "#comment-" + str(comment.id)

    def _notify(sub):
        notify(sub, "ticket_comment", "Re: {}/{}/#{}: {}".format(
            tracker.owner.canonical_name(), tracker.name,
            ticket.scoped_id, ticket.title),
                headers={
                    "From": "~{} <{}>".format(
                        user.username, notify_from),
                    "Sender": smtp_user,
                },
                ticket=ticket,
                comment=comment,
                resolution=resolution.name if resolution else None,
                ticket_url=ticket_url.replace("%7E", "~")) # hack

    event = Event()
    event.event_type = 0
    event.user_id = user.id
    event.ticket_id = ticket.id
    if comment:
        event.event_type |= EventType.comment
        event.comment_id = comment.id
    if ticket.status != old_status or ticket.resolution != old_resolution:
        event.event_type |= EventType.status_change
        event.old_status = old_status
        event.old_resolution = old_resolution
        event.new_status = ticket.status
        event.new_resolution = ticket.resolution
    db.session.add(event)
    db.session.flush()

    def _add_notification(sub):
        notification = EventNotification()
        notification.user_id = sub.user_id
        notification.event_id = event.id
        db.session.add(notification)

    subscribed = False
    updated_users = set()
    for sub in tracker.subscriptions:
        updated_users.update([sub.user_id])
        _add_notification(sub)
        if sub.user_id == user.id:
            subscribed = True
            continue
        _notify(sub)

    for sub in ticket.subscriptions:
        if sub.user_id in updated_users:
            continue
        _add_notification(sub)
        if sub.user_id == user.id:
            subscribed = True
            continue
        _notify(sub)

    if not subscribed:
        sub = TicketSubscription()
        sub.ticket_id = ticket.id
        sub.user_id = user.id
        db.session.add(sub)
        _add_notification(sub)

    db.session.commit()

    return comment
