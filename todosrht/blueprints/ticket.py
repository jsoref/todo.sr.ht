import re
import string
from flask import Blueprint, render_template, request, url_for, abort, redirect
from flask import session
from flask_login import current_user
from todosrht.access import get_tracker, get_ticket
from todosrht.types import Tracker, User, Ticket, TicketStatus, TicketAccess
from todosrht.types import TicketComment, TicketResolution, TicketSeen
from todosrht.types import TicketSubscription
from todosrht.types import Event, EventType, EventNotification
from todosrht.types import Label, TicketLabel
from todosrht.email import notify
from srht.config import cfg
from srht.database import db
from srht.flask import loginrequired
from srht.validation import Validation
from datetime import datetime

ticket = Blueprint("ticket", __name__)

smtp_user = cfg("mail", "smtp-user", default=None)
smtp_from = cfg("mail", "smtp-from", default=None)
notify_from = cfg("todo.sr.ht", "notify-from", default=smtp_from)

@ticket.route("/<owner>/<name>/<int:ticket_id>")
def ticket_GET(owner, name, ticket_id):
    tracker, _ = get_tracker(owner, name)
    if not tracker:
        abort(404)
    ticket, access = get_ticket(tracker, ticket_id)
    if not ticket:
        abort(404)
    is_subscribed = False
    tracker_sub = None
    if current_user:
        seen = (TicketSeen.query
                .filter(TicketSeen.user_id == current_user.id,
                    TicketSeen.ticket_id == ticket.id)
                .one_or_none())
        if not seen:
            seen = TicketSeen(user_id=current_user.id, ticket_id=ticket.id)
        seen.update()
        db.session.add(seen)
        db.session.commit()

        tracker_sub = (TicketSubscription.query
            .filter(TicketSubscription.ticket_id == None)
            .filter(TicketSubscription.tracker_id == tracker.id)
            .filter(TicketSubscription.user_id == current_user.id)
        ).one_or_none()

        sub = (TicketSubscription.query
        .filter(TicketSubscription.tracker_id == None)
            .filter(TicketSubscription.ticket_id == ticket.id)
            .filter(TicketSubscription.user_id == current_user.id)
        ).one_or_none()

        is_subscribed = bool(sub)

    return render_template("ticket.html", tracker=tracker, ticket=ticket,
            access=access, is_subscribed=is_subscribed, tracker_sub=tracker_sub)

@ticket.route("/<owner>/<name>/<int:ticket_id>/enable_notifications", methods=["POST"])
@loginrequired
def enable_notifications(owner, name, ticket_id):
    tracker, access = get_tracker(owner, name)
    if not tracker:
        abort(404)
    ticket, access = get_ticket(tracker, ticket_id)
    if not ticket:
        abort(404)

    sub = (TicketSubscription.query
        .filter(TicketSubscription.tracker_id == None)
        .filter(TicketSubscription.ticket_id == ticket.id)
        .filter(TicketSubscription.user_id == current_user.id)
    ).one_or_none()

    if sub:
        return redirect(url_for(".ticket_GET",
            owner=owner, name=name, ticket_id=ticket.scoped_id))

    sub = TicketSubscription()
    sub.ticket_id = ticket.id
    sub.user_id = current_user.id
    db.session.add(sub)
    db.session.commit()
    return redirect(url_for(".ticket_GET",
        owner=owner, name=name, ticket_id=ticket.scoped_id))

@ticket.route("/<owner>/<name>/<int:ticket_id>/disable_notifications", methods=["POST"])
@loginrequired
def disable_notifications(owner, name, ticket_id):
    tracker, access = get_tracker(owner, name)
    if not tracker:
        abort(404)
    ticket, access = get_ticket(tracker, ticket_id)
    if not ticket:
        abort(404)

    sub = (TicketSubscription.query
        .filter(TicketSubscription.tracker_id == None)
        .filter(TicketSubscription.ticket_id == ticket.id)
        .filter(TicketSubscription.user_id == current_user.id)
    ).one_or_none()

    if not sub:
        return redirect(url_for(".ticket_GET",
            owner=owner, name=name, ticket_id=ticket.scoped_id))

    db.session.delete(sub)
    db.session.commit()
    return redirect(url_for(".ticket_GET",
        owner=owner, name=name, ticket_id=ticket.scoped_id))

@ticket.route("/<owner>/<name>/<int:ticket_id>/comment", methods=["POST"])
@loginrequired
def ticket_comment_POST(owner, name, ticket_id):
    tracker, access = get_tracker(owner, name)
    if not tracker:
        abort(404)
    ticket, access = get_ticket(tracker, ticket_id)
    if not ticket:
        abort(404)

    valid = Validation(request)
    text = valid.optional("comment")
    resolve = valid.optional("resolve")
    resolution = valid.optional("resolution")
    reopen = valid.optional("reopen")

    valid.expect(not text or 3 < len(text) < 16384,
            "Comment must be between 3 and 16384 characters.", field="comment")

    valid.expect(text or resolve or reopen,
            "Comment is required", field="comment")

    if not valid.ok:
        return render_template("ticket.html",
                tracker=tracker,
                ticket=ticket,
                access=access,
                **valid.kwargs)

    if text:
        comment = TicketComment()
        comment.text = text
        # TODO: anonymous comments (when configured appropriately)
        comment.submitter_id = current_user.id
        comment.ticket_id = ticket.id
        db.session.add(comment)
        ticket.updated = comment.created
    else:
        comment = None

    old_status = ticket.status
    old_resolution = ticket.resolution

    if resolve and TicketAccess.edit in access:
        try:
            resolution = TicketResolution(int(resolution))
            ticket.status = TicketStatus.resolved
            ticket.resolution = resolution
        except Exception as ex:
            valid.expect(text, "Comment is required", field="comment")
    else:
        resolution = None

    if reopen and TicketAccess.edit in access:
        ticket.status = TicketStatus.reported

    if not valid.ok:
        return render_template("ticket.html",
                tracker=tracker,
                ticket=ticket,
                access=access,
                **valid.kwargs)

    tracker.updated = datetime.utcnow()
    db.session.flush()

    if comment:
        ticket_url = url_for(".ticket_GET",
                owner=tracker.owner.canonical_name(),
                name=tracker.name,
                ticket_id=ticket.scoped_id) + "#comment-" + str(comment.id)
    else:
        ticket_url = url_for(".ticket_GET",
            owner=tracker.owner.canonical_name(),
            name=tracker.name,
            ticket_id=ticket.scoped_id)

    subscribed = False

    def _notify(sub):
        notify(sub, "ticket_comment", "Re: {}/{}/#{}: {}".format(
            tracker.owner.canonical_name(), tracker.name,
            ticket.scoped_id, ticket.title),
                headers={
                    "From": "~{} <{}>".format(
                        current_user.username, notify_from),
                    "Sender": smtp_user,
                },
                ticket=ticket,
                comment=comment,
                resolution=resolution.name if resolution else None,
                ticket_url=ticket_url.replace("%7E", "~")) # hack

    event = Event()
    event.event_type = 0
    event.user_id = current_user.id
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
        if sub.user_id == current_user.id:
            subscribed = True
            continue
        _notify(sub)

    for sub in ticket.subscriptions:
        if sub.user_id in updated_users:
            continue
        _add_notification(sub)
        if sub.user_id == current_user.id:
            subscribed = True
            continue
        _notify(sub)

    if not subscribed:
        sub = TicketSubscription()
        sub.ticket_id = ticket.id
        sub.user_id = current_user.id
        db.session.add(sub)
        _add_notification(sub)

    db.session.commit()

    return redirect(ticket_url)

@ticket.route("/<owner>/<name>/<int:ticket_id>/edit")
@loginrequired
def ticket_edit_GET(owner, name, ticket_id):
    tracker, _ = get_tracker(owner, name)
    if not tracker:
        abort(404)
    ticket, access = get_ticket(tracker, ticket_id)
    if not ticket:
        abort(404)
    if not TicketAccess.edit in access:
        abort(401)
    return render_template("edit_ticket.html",
            tracker=tracker, ticket=ticket)

@ticket.route("/<owner>/<name>/<int:ticket_id>/edit", methods=["POST"])
@loginrequired
def ticket_edit_POST(owner, name, ticket_id):
    tracker, _ = get_tracker(owner, name)
    if not tracker:
        abort(404)
    ticket, access = get_ticket(tracker, ticket_id)
    if not ticket:
        abort(404)
    if not TicketAccess.edit in access:
        abort(401)

    valid = Validation(request)
    title = valid.require("title", friendly_name="Title")
    desc = valid.optional("description")

    valid.expect(not title or 3 <= len(title) <= 2048,
            "Title must be between 3 and 2048 characters.",
            field="title")
    valid.expect(not desc or len(desc) < 16384,
            "Description must be no more than 16384 characters.",
            field="description")

    if not valid.ok:
        return render_template("edit_ticket.html",
                tracker=tracker, ticket=ticket, **valid.kwargs)

    ticket.title = title
    ticket.description = desc
    db.session.commit()

    return redirect(url_for("ticket.ticket_GET",
            owner=tracker.owner.canonical_name(),
            name=name,
            ticket_id=ticket.scoped_id))

@ticket.route("/<owner>/<name>/<int:ticket_id>/add_label", methods=["POST"])
@loginrequired
def ticket_add_label(owner, name, ticket_id):
    tracker, _ = get_tracker(owner, name)
    if not tracker:
        abort(404)
    ticket, access = get_ticket(tracker, ticket_id)
    if not ticket:
        abort(404)
    if not TicketAccess.edit in access:
        abort(401)

    label_id = int(request.form.get('label_id'))
    label = Label.query.filter(Label.id==label_id).first()
    if not label:
        abort(404)

    ticket_label = (TicketLabel.query
            .filter(TicketLabel.label_id == label.id)
            .filter(TicketLabel.ticket_id == ticket_id)).first()

    if not ticket_label:
        ticket_label = TicketLabel()
        ticket_label.ticket_id = ticket_id
        ticket_label.label_id = label.id
        ticket_label.user_id = current_user.id

        db.session.add(ticket_label)
        db.session.commit()

    return redirect(url_for("ticket.ticket_GET",
            owner=tracker.owner.canonical_name(),
            name=name,
            ticket_id=ticket_id))
