import re
import string
from flask import Blueprint, render_template, request, url_for, abort, redirect
from flask_login import current_user
from todosrht.decorators import loginrequired
from todosrht.types import Tracker, User
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

@tracker.route("/<owner>/<path:name>")
def tracker_GET(owner, name):
    if owner.startswith("~"):
        owner = User.query.filter(User.username == owner[1:]).first()
        if not owner:
            abort(404)
        print(name)
        tracker = (Tracker.query
                .filter(Tracker.owner_id == owner.id)
                .filter(Tracker.name == name.lower())
            ).first()
        if not tracker:
            abort(404)
    else:
        abort(404) # TODO
    return render_template("tracker.html", tracker=tracker)

@tracker.route("/<owner>/<path:name>/configure")
@loginrequired
def tracker_configure_GET(owner, name):
    pass

@tracker.route("/<owner>/<path:name>/submit")
@loginrequired
def tracker_submit_GET(owner, name):
    pass
