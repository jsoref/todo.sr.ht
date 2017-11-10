import re
import string
from sqlalchemy import or_
from flask import Blueprint, render_template, request, url_for, abort, redirect
from flask import session
from flask_login import current_user
from todosrht.decorators import loginrequired
from todosrht.email import notify
from todosrht.types import Tracker, User, Ticket, TicketStatus, TicketAccess
from todosrht.types import TicketComment, TicketResolution, TicketSubscription
from todosrht.types import TicketSeen, Event, EventType, EventNotification
from srht.config import cfg
from srht.database import db
from srht.validation import Validation
from datetime import datetime

tracker = Blueprint("tracker", __name__)

name_re = re.compile(r"^([a-z][a-z0-9_.-]*/?)+$")

smtp_user = cfg("mail", "smtp-user", default=None)

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
    db.session.flush()

    sub = TicketSubscription()
    sub.tracker_id = tracker.id
    sub.user_id = current_user.id
    db.session.add(sub)

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
                .filter(Tracker.name == name.lower().rstrip("/"))
            ).first()
        if not tracker:
            return None, None
        access = get_access(tracker, None)
        if access:
            return tracker, access
        return None, None

    # TODO: org trackers
    return None, None

def apply_search(query, search):
    terms = search.split(" ")
    for term in terms:
        term = term.lower()
        if ":" in term:
            prop, value = term.split(":")
        else:
            prop, value = None, term

        if prop == "status" :
            status_aliases = {
                "closed": "resolved"
            }
            if value in status_aliases:
                value = status_aliases[value]
            if hasattr(TicketStatus, value):
                status = getattr(TicketStatus, value)
                query = query.filter(Ticket.status == status)
                continue

        if prop == "submitter":
            user = User.query.filter(User.username == value).first()
            if user:
                query = query.filter(Ticket.submitter_id == user.id)
                continue

        query = query.filter(or_(
            Ticket.description.ilike("%" + value + "%"),
            Ticket.title.ilike("%" + value + "%")))

    return query

def return_tracker(tracker, access, **kwargs):
    another = session.get("another") or False
    if another:
        del session["another"]
    is_subscribed = False
    if current_user:
        is_subscribed = TicketSubscription.query.filter(
                TicketSubscription.tracker_id == tracker.id,
                TicketSubscription.user_id == current_user.id).count() > 0
    page = request.args.get("page")
    tickets = Ticket.query.filter(Ticket.tracker_id == tracker.id)

    search = request.args.get("search")
    tickets = tickets.order_by(Ticket.updated.desc())
    if search:
        tickets = apply_search(tickets, search)
    else:
        tickets = tickets.filter(Ticket.status == TicketStatus.reported)

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
            is_subscribed=is_subscribed,
            search=search,
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
    tracker.updated = datetime.utcnow()
    # TODO: Handle unique constraint failure (contention) and retry?
    db.session.flush()
    event = Event()
    event.event_type = EventType.created
    event.user_id = current_user.id
    event.ticket_id = ticket.id
    db.session.add(event)
    db.session.flush()
    
    ticket_url = url_for("ticket.ticket_GET",
            owner="~" + tracker.owner.username,
            name=name,
            ticket_id=ticket.scoped_id)

    for sub in tracker.subscriptions:
        notification = EventNotification()
        notification.user_id = sub.user_id
        notification.event_id = event.id
        db.session.add(notification)

        if sub.user_id == ticket.submitter_id:
            subscribed = True
            continue
        notify(sub, "new_ticket", "#{}: {}".format(ticket.id, ticket.title),
                headers={
                    "From": "{} <{}>".format(current_user.username,
                        current_user.email),
                    "Sender": smtp_user
                }, ticket=ticket,
                ticket_url=ticket_url.replace("%7E", "~")) # hack

    if not subscribed:
        sub = TicketSubscription()
        sub.ticket_id = ticket.id
        sub.user_id = user.id
        db.session.add(sub)

    db.session.commit()

    if another:
        session["another"] = True
        return redirect(url_for(".tracker_GET",
                owner="~" + tracker.owner.username,
                name=name))
    else:
        return redirect(ticket_url)
