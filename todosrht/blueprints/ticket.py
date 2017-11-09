import re
import string
from flask import Blueprint, render_template, request, url_for, abort, redirect
from flask import session
from flask_login import current_user
from todosrht.decorators import loginrequired
from todosrht.types import Tracker, User, Ticket, TicketStatus, TicketAccess, TicketSeen
from todosrht.types import TicketComment, TicketResolution
from todosrht.blueprints.tracker import get_access, get_tracker
from todosrht.email import notify
from srht.config import cfg
from srht.database import db
from srht.validation import Validation

ticket = Blueprint("ticket", __name__)

smtp_user = cfg("mail", "smtp-user", default=None)

def get_ticket(tracker, ticket_id):
    ticket = (Ticket.query
            .filter(Ticket.scoped_id == ticket_id)
            .filter(Ticket.tracker_id == tracker.id)
        ).first()
    if not ticket:
        return None, None
    access = get_access(tracker, ticket)
    if not TicketAccess.browse in access:
        return None, None
    return ticket, access

@ticket.route("/<owner>/<path:name>/<int:ticket_id>")
def ticket_GET(owner, name, ticket_id):
    tracker, _ = get_tracker(owner, name)
    if not tracker:
        abort(404)
    ticket, access = get_ticket(tracker, ticket_id)
    if not ticket:
        abort(404)
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
    return render_template("ticket.html",
            tracker=tracker,
            ticket=ticket,
            access=access)

@ticket.route("/<owner>/<path:name>/<int:ticket_id>/comment", methods=["POST"])
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
            "Comment must be between 3 and 16384 characters.")

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

    db.session.commit()

    if comment:
        ticket_url = url_for(".ticket_GET",
                owner="~" + tracker.owner.username,
                name=tracker.name,
                ticket_id=ticket.scoped_id) + "#comment-" + str(comment.id)
    else:
        ticket_url = url_for(".ticket_GET",
            owner="~" + tracker.owner.username,
            name=tracker.name,
            ticket_id=ticket.scoped_id)

    subscribed = False

    def _notify(sub):
        notify(sub, "ticket_comment", "Re: #{}: {}".format(
            ticket.id, ticket.title),
                headers={
                    "From": "{} <{}>".format(
                        current_user.username,
                        current_user.email),
                    "Sender": smtp_user
                },
                ticket=ticket,
                comment=comment,
                resolution=resolution.name if resolution else None,
                ticket_url=ticket_url.replace("%7E", "~")) # hack

    for sub in tracker.subscriptions:
        if sub.user_id == comment.submitter_id:
            subscribed = True
            continue
        _notify(sub)

    for sub in ticket.subscriptions:
        if sub.user_id == comment.submitter_id:
            subscribed = True
            continue
        _notify(sub)

    if not subscribed:
        sub = TicketSubscription()
        sub.ticket_id = ticket.id
        sub.user_id = user.id
        db.session.add(sub)
        db.session.commit()

    return redirect(ticket_url)
