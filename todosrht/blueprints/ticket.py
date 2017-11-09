import re
import string
from flask import Blueprint, render_template, request, url_for, abort, redirect
from flask import session
from flask_login import current_user
from todosrht.decorators import loginrequired
from todosrht.types import Tracker, User, Ticket, TicketStatus, TicketAccess, TicketSeen
from todosrht.types import TicketComment, TicketResolution
from todosrht.blueprints.tracker import get_access, get_tracker
from srht.validation import Validation
from srht.database import db

ticket = Blueprint("ticket", __name__)

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
        return redirect(url_for(".ticket_GET",
                owner="~" + tracker.owner.username,
                name=tracker.name,
                ticket_id=ticket.scoped_id) + "#comment-" + str(comment.id))

    return redirect(url_for(".ticket_GET",
            owner="~" + tracker.owner.username,
            name=tracker.name,
            ticket_id=ticket.scoped_id))
