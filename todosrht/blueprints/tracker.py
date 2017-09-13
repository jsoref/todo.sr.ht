import re
import string
from flask import Blueprint, render_template, request, url_for, abort, redirect
from flask import session
from flask_login import current_user
from todosrht.decorators import loginrequired
from todosrht.types import Tracker, User, Ticket
from srht.validation import Validation
from srht.database import db

tracker = Blueprint("tracker", __name__)

name_re = re.compile(r"^([a-z][a-z0-9_.-]*/?)+$")

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
            return None
        tracker = (Tracker.query
                .filter(Tracker.owner_id == owner.id)
                .filter(Tracker.name == name.lower())
            ).first()
        return tracker
    else:
        # TODO: org trackers
        return None

@tracker.route("/<owner>/<path:name>")
def tracker_GET(owner, name):
    tracker = get_tracker(owner, name)
    if not tracker:
        abort(404)
    another = session.get("another") or False
    if another:
        del session["another"]
    return render_template("tracker.html", tracker=tracker, another=another)

@tracker.route("/<owner>/<path:name>/configure")
@loginrequired
def tracker_configure_GET(owner, name):
    pass

@tracker.route("/<owner>/<path:name>/submit", methods=["POST"])
@loginrequired
def tracker_submit_GET(owner, name):
    tracker = get_tracker(owner, name)
    if not tracker:
        abort(404)

    valid = Validation(request)
    title = valid.require("title", friendly_name="Title")
    desc = valid.require("description", friendly_name="Description")
    another = valid.optional("another")

    valid.expect(not title or 3 < len(title) < 2048,
            "Title must be between 3 and 2048 characters.",
            field="title")
    valid.expect(not desc or len(desc) < 2048,
            "Description must be no more than 16384 characters.",
            field="description")

    if not valid.ok:
        return render_template("tracker.html",
                tracker=tracker,
                **valid.kwargs), 400

    ticket = Ticket()
    ticket.submitter_id = current_user.id
    ticket.tracker_id = tracker.id
    ticket.user_agent = request.headers.get("User-Agent")
    ticket.title = title
    ticket.description = desc
    db.session.add(ticket)
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
                ticket_id=ticket.id))

@tracker.route("/<owner>/<path:name>/<int:ticket_id>")
def ticket_GET(owner, name, ticket_id):
    pass
