import re
from flask import Blueprint, render_template, request, abort, redirect
from flask_login import current_user
from srht.database import db
from srht.flask import loginrequired
from srht.validation import Validation
from todosrht.access import get_tracker, get_ticket
from todosrht.tickets import add_comment, mark_seen, assign, unassign
from todosrht.types import Event, EventType
from todosrht.types import Label, TicketLabel
from todosrht.types import TicketAccess, TicketResolution
from todosrht.types import TicketSubscription, User
from todosrht.urls import ticket_url

ticket = Blueprint("ticket", __name__)


def get_ticket_context(ticket, tracker, access):
    """Returns the context required to render ticket.html"""
    tracker_sub = None
    ticket_sub = None

    if current_user:
        tracker_sub = TicketSubscription.query.filter_by(
            ticket=None, tracker=tracker, user=current_user).one_or_none()
        ticket_sub = TicketSubscription.query.filter_by(
            ticket=ticket, tracker=None, user=current_user).one_or_none()

    return {
        "tracker": tracker,
        "ticket": ticket,
        "access": access,
        "tracker_sub": tracker_sub,
        "ticket_sub": ticket_sub,
    }

@ticket.route("/<owner>/<name>/<int:ticket_id>")
def ticket_GET(owner, name, ticket_id):
    tracker, _ = get_tracker(owner, name)
    if not tracker:
        abort(404)
    ticket, access = get_ticket(tracker, ticket_id)
    if not ticket:
        abort(404)

    if current_user:
        mark_seen(ticket, current_user)
        db.session.commit()

    ctx = get_ticket_context(ticket, tracker, access)
    return render_template("ticket.html", **ctx)

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
        return redirect(ticket_url(ticket))

    sub = TicketSubscription()
    sub.ticket_id = ticket.id
    sub.user_id = current_user.id
    db.session.add(sub)
    db.session.commit()
    return redirect(ticket_url(ticket))

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
        return redirect(ticket_url(ticket))

    db.session.delete(sub)
    db.session.commit()
    return redirect(ticket_url(ticket))

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

    if (resolve or reopen) and TicketAccess.edit not in access:
        abort(403)

    if resolve:
        try:
            resolution = TicketResolution(int(resolution))
        except Exception as ex:
            abort(400, "Invalid resolution")
    else:
        resolution = None

    if not valid.ok:
        ctx = get_ticket_context(ticket, tracker, access)
        return render_template("ticket.html", **ctx, **valid.kwargs)

    comment = add_comment(current_user, ticket,
        text=text, resolve=resolve, resolution=resolution, reopen=reopen)

    return redirect(ticket_url(ticket, comment))

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

    return redirect(ticket_url(ticket))

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

    valid = Validation(request)
    label_id = valid.require("label_id", friendly_name="A label")
    if not valid.ok:
        ctx = get_ticket_context(ticket, tracker, access)
        return render_template("ticket.html", **ctx, **valid.kwargs)

    valid.expect(re.match(r"^\d+$", label_id),
            "Label ID must be numeric", field="label_id")
    if not valid.ok:
        ctx = get_ticket_context(ticket, tracker, access)
        return render_template("ticket.html", **ctx, **valid.kwargs)

    label_id = int(request.form.get('label_id'))
    label = Label.query.filter(Label.id == label_id).first()
    if not label:
        abort(404)

    ticket_label = (TicketLabel.query
            .filter(TicketLabel.label_id == label.id)
            .filter(TicketLabel.ticket_id == ticket.id)).first()

    if not ticket_label:
        ticket_label = TicketLabel()
        ticket_label.ticket_id = ticket.id
        ticket_label.label_id = label.id
        ticket_label.user_id = current_user.id

        event = Event()
        event.event_type = EventType.label_added
        event.user_id = current_user.id
        event.ticket_id = ticket.id
        event.label_id = label.id

        db.session.add(ticket_label)
        db.session.add(event)
        db.session.commit()

    return redirect(ticket_url(ticket))

@ticket.route("/<owner>/<name>/<int:ticket_id>/remove_label/<int:label_id>",
        methods=["POST"])
@loginrequired
def ticket_remove_label(owner, name, ticket_id, label_id):
    tracker, _ = get_tracker(owner, name)
    if not tracker:
        abort(404)
    ticket, access = get_ticket(tracker, ticket_id)
    if not ticket:
        abort(404)
    if not TicketAccess.edit in access:
        abort(401)
    label = Label.query.filter(Label.id==label_id).first()
    if not label:
        abort(404)

    ticket_label = (TicketLabel.query
            .filter(TicketLabel.label_id == label_id)
            .filter(TicketLabel.ticket_id == ticket.id)).first()

    if ticket_label:
        event = Event()
        event.event_type = EventType.label_removed
        event.user_id = current_user.id
        event.ticket_id = ticket.id
        event.label_id = label.id

        db.session.add(event)
        db.session.delete(ticket_label)
        db.session.commit()

    return redirect(ticket_url(ticket))

def _assignment_get_ticket(owner, name, ticket_id):
    tracker, _ = get_tracker(owner, name)
    if not tracker:
        abort(404)

    ticket, access = get_ticket(tracker, ticket_id)
    if not ticket:
        abort(404)
    if TicketAccess.edit not in access:
        abort(401)

    return ticket

def _assignment_get_user(valid):
    username = valid.optional('username')
    if not username:
        if 'myself' in valid:
            username = current_user.username
        else:
            valid.error("Username is required", field="username")
    if not valid.ok:
        return None
    if username.startswith("~"):
        username = username[1:]

    user = User.query.filter_by(username=username).one_or_none()
    valid.expect(user, "User not found.", field="username")
    return user

@ticket.route("/<owner>/<name>/<int:ticket_id>/assign", methods=["POST"])
@loginrequired
def ticket_assign(owner, name, ticket_id):
    valid = Validation(request)
    ticket = _assignment_get_ticket(owner, name, ticket_id)
    user = _assignment_get_user(valid)
    if not valid.ok:
        _, access = get_ticket(ticket.tracker, ticket_id)
        ctx = get_ticket_context(ticket, ticket.tracker, access)
        return render_template("ticket.html", **valid.kwargs, **ctx)

    assign(ticket, user, current_user)
    db.session.commit()

    return redirect(ticket_url(ticket))

@ticket.route("/<owner>/<name>/<int:ticket_id>/unassign", methods=["POST"])
@loginrequired
def ticket_unassign(owner, name, ticket_id):
    valid = Validation(request)
    ticket = _assignment_get_ticket(owner, name, ticket_id)
    user = _assignment_get_user(valid)
    if not valid.ok:
        ctx = get_ticket_context(ticket, ticket.tracker, access)
        return render_template("ticket.html", valid, **ctx)

    unassign(ticket, user)
    db.session.commit()

    return redirect(ticket_url(ticket))
