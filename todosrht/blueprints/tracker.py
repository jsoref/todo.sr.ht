import re
import string
from flask import Blueprint, render_template, request, url_for, abort, redirect
from flask import session
from flask_login import current_user
from todosrht.decorators import loginrequired
from todosrht.types import Tracker, User, Ticket, TicketStatus, TicketAccess, TicketSeen
from todosrht.types import TicketComment, TicketResolution
from srht.validation import Validation
from srht.database import db

tracker = Blueprint("tracker", __name__)

name_re = re.compile(r"^([a-z][a-z0-9_.-]*/?)+$")

def get_access(tracker, ticket):
    # TODO: flesh out
    if current_user and current_user.id == tracker.owner_id:
        return TicketAccess.all
    elif current_user:
        if ticket and current_user.id == ticket.submitter_id:
            return ticket.submitter_perms or tracker.default_submitter_perms
        return tracker.default_submitter_perms

    if ticket:
        return ticket.anonymous_perms
    return tracker.default_anonymous_perms


@tracker.route("/tracker/create")
@loginrequired
def create_GET():
    return render_template("tracker-create.html")

@tracker.route("/tracker/create", methods=["POST"])
@loginrequired
def create_POST():
    valid = Validation(request)
    name = valid.require("tracker_name", friendly_name="Name")
    desc = valid.optional("tracker_desc")
    if not valid.ok:
        return render_template("tracker-create.html", **valid.kwargs), 400

    valid.expect(2 < len(name) < 256,
            "Must be between 2 and 256 characters",
            field="tracker_name")
    valid.expect(not valid.ok or name[0] in string.ascii_lowercase,
            "Must begin with a lowercase letter", field="tracker_name")
    valid.expect(not valid.ok or name_re.match(name),
            "Only lowercase alphanumeric characters or -./",
            field="tracker_name")
    valid.expect(not desc or len(desc) < 4096,
            "Must be less than 4096 characters",
            field="tracker_desc")
    if not valid.ok:
        return render_template("tracker-create.html", **valid.kwargs), 400

    tracker = (Tracker.query
            .filter(Tracker.owner_id == current_user.id)
            .filter(Tracker.name == name)
        ).first()
    valid.expect(not tracker,
            "A tracker by this name already exists",
            field="tracker_name")
    if not valid.ok:
        return render_template("tracker-create.html", **valid.kwargs), 400

    tracker = Tracker()
    tracker.owner_id = current_user.id
    tracker.name = name
    tracker.description = desc
    db.session.add(tracker)
    db.session.commit()

    if "create-configure" in valid:
        return redirect(url_for(".tracker_configure_GET",
                owner=current_user.username,
                name=name))

    return redirect(url_for(".tracker_GET",
            owner="~" + current_user.username,
            name=name))

def get_tracker(owner, name):
    if owner.startswith("~"):
        owner = User.query.filter(User.username == owner[1:]).first()
        if not owner:
            return None, None
        tracker = (Tracker.query
                .filter(Tracker.owner_id == owner.id)
                .filter(Tracker.name == name.lower())
            ).first()
        if not tracker:
            return None, None
        access = get_access(tracker, None)
        if access:
            return tracker, access
        return None, None

    # TODO: org trackers
    return None, None

def return_tracker(tracker, access, **kwargs):
    another = session.get("another") or False
    if another:
        del session["another"]
    # TODO: Apply filtering here
    page = request.args.get("page")
    tickets = (Ticket.query
            .filter(Ticket.tracker_id == tracker.id)
            .filter(Ticket.status == TicketStatus.reported)
            .order_by(Ticket.updated.desc())
        )
    per_page = 25
    total_tickets = tickets.count()
    total_pages = tickets.count() // per_page + 1
    if total_tickets % per_page == 0:
        total_pages -= 1
    if page:
        try:
            page = int(page) - 1
            tickets = tickets.offset(page * per_page)
        except:
            page = None
    else:
        page = 0
    tickets = tickets.limit(per_page).all()
    if "another" in kwargs:
        another = kwargs["another"]
        del kwargs["another"]
    return render_template("tracker.html",
            tracker=tracker,
            another=another,
            tickets=tickets,
            total_tickets=total_tickets,
            total_pages=total_pages,
            page=page + 1,
            access=access,
            **kwargs)

@tracker.route("/<owner>/<path:name>")
def tracker_GET(owner, name):
    tracker, access = get_tracker(owner, name)
    if not tracker:
        abort(404)
    return return_tracker(tracker, access)

@tracker.route("/<owner>/<path:name>/configure")
@loginrequired
def tracker_configure_GET(owner, name):
    pass

@tracker.route("/<owner>/<path:name>/submit", methods=["POST"])
@loginrequired
def tracker_submit_POST(owner, name):
    tracker, access = get_tracker(owner, name)
    if not tracker:
        abort(404)

    valid = Validation(request)
    title = valid.require("title", friendly_name="Title")
    desc = valid.optional("description")
    another = valid.optional("another")

    valid.expect(not title or 3 <= len(title) <= 2048,
            "Title must be between 3 and 2048 characters.",
            field="title")
    valid.expect(not desc or len(desc) < 16384,
            "Description must be no more than 16384 characters.",
            field="description")

    if not valid.ok:
        return return_tracker(tracker, **valid.kwargs), 400

    ticket = Ticket()
    ticket.submitter_id = current_user.id
    ticket.tracker_id = tracker.id
    ticket.scoped_id = tracker.next_ticket_id
    tracker.next_ticket_id += 1
    ticket.user_agent = request.headers.get("User-Agent")
    ticket.title = title
    ticket.description = desc
    db.session.add(ticket)
    # TODO: Handle unique constraint failure (contention) and retry?
    db.session.commit()

    if another:
        session["another"] = True
        return redirect(url_for(".tracker_GET",
                owner="~" + tracker.owner.username,
                name=name))
    else:
        return redirect(url_for(".ticket_GET",
                owner="~" + tracker.owner.username,
                name=name,
                ticket_id=ticket.scoped_id))

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

@tracker.route("/<owner>/<path:name>/<int:ticket_id>")
def ticket_GET(owner, name, ticket_id):
    tracker, _ = get_tracker(owner, name)
    if not tracker:
        abort(404)
    ticket, access = get_ticket(tracker, ticket_id)
    if not ticket:
        abort(404)
    seen = (TicketSeen.query
            .filter(TicketSeen.user_id == current_user.id,
                TicketSeen.ticket_id == ticket.id)
            .one_or_none()) if current_user else None
    if not seen:
        seen = TicketSeen(user_id=current_user.id, ticket_id=ticket.id)
    seen.update()
    db.session.add(seen)
    db.session.commit()
    return render_template("ticket.html",
            tracker=tracker,
            ticket=ticket,
            access=access)

@tracker.route("/<owner>/<path:name>/<int:ticket_id>/comment", methods=["POST"])
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
