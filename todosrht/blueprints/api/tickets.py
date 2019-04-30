from flask import Blueprint, abort, request
from srht.api import paginated_response
from srht.database import db
from srht.oauth import oauth, current_token
from srht.validation import Validation
from todosrht.access import get_tracker, get_ticket
from todosrht.tickets import submit_ticket, add_comment
from todosrht.blueprints.api import get_user
from todosrht.types import Ticket, TicketAccess, TicketStatus, TicketResolution

tickets = Blueprint("api.tickets", __name__)

@tickets.route("/api/user/<username>/trackers/<tracker_name>/tickets")
@tickets.route("/api/trackers/<tracker_name>/tickets",
        defaults={"username": None})
@oauth("tickets:read")
def tracker_tickets_GET(username, tracker_name):
    user = get_user(username)
    tracker, access = get_tracker(user, tracker_name, user=current_token.user)
    if not tracker:
        abort(404)
    if not TicketAccess.browse in access:
        abort(401)
    tickets = (Ticket.query
        .filter(Ticket.tracker_id == tracker.id)
        .order_by(Ticket.scoped_id.desc()))
    return paginated_response(Ticket.scoped_id, tickets)

@tickets.route("/api/user/<username>/trackers/<tracker_name>/tickets",
        methods=["POST"])
@tickets.route("/api/trackers/<tracker_name>/tickets",
        defaults={"username": None}, methods=["POST"])
@oauth("tickets:write")
def tracker_tickets_POST(username, tracker_name):
    user = get_user(username)
    tracker, access = get_tracker(user, tracker_name, user=current_token.user)
    if not tracker:
        abort(404)
    if not TicketAccess.submit in access:
        abort(401)

    valid = Validation(request)
    title = valid.require("title")
    desc = valid.require("description")
    valid.expect(not title or 3 <= len(title) <= 2048,
            "Title must be between 3 and 2048 characters.",
            field="title")
    valid.expect(not desc or len(desc) < 16384,
            "Description must be no more than 16384 characters.",
            field="description")
    if not valid.ok:
        return valid.response

    ticket = submit_ticket(tracker, current_token.user, title, desc)
    return ticket.to_dict(), 201

@tickets.route("/api/user/<username>/trackers/<tracker_name>/tickets/<ticket_id>")
@tickets.route("/api/trackers/<tracker_name>/tickets/<ticket_id>",
        defaults={"username": None})
@oauth("tickets:read")
def tracker_ticket_by_id_GET(username, tracker_name, ticket_id):
    user = get_user(username)
    tracker, _ = get_tracker(user, tracker_name, user=current_token.user)
    if not tracker:
        abort(404)
    ticket, access = get_ticket(tracker, ticket_id, user=current_token.user)
    if not TicketAccess.browse in access:
        abort(401)
    return ticket.to_dict()

@tickets.route("/api/user/<username>/trackers/<tracker_name>/tickets/<ticket_id>",
        methods=["PUT"])
@tickets.route("/api/trackers/<tracker_name>/tickets/<ticket_id>",
        defaults={"username": None}, methods=["PUT"])
@oauth("tickets:write")
def tracker_ticket_by_id_PUT(username, tracker_name, ticket_id):
    user = get_user(username)
    tracker, _ = get_tracker(user, tracker_name, user=current_token.user)
    if not tracker:
        abort(404)
    ticket, access = get_ticket(tracker, ticket_id, user=current_token.user)

    required_access = TicketAccess.none
    valid = Validation(request)
    comment = resolution = None
    resolve = reopen = False
    if "comment" in valid:
        comment = valid.optional("comment")
        valid.expect(not comment or 3 <= len(comment) <= 16384,
                "Comment must be between 3 and 16384 characters.",
                field="comment")
    if "status" in valid:
        status = valid.optional("status",
                cls=TicketStatus, default=valid.status)
        if status != ticket.status:
            if status != TicketStatus.open:
                resolve = True
                resolution = valid.require("resolution", cls=TicketResolution)
            else:
                reopen = True

    event = add_comment(user, ticket, comment, resolve, resolution, reopen)
    return event.to_dict()
