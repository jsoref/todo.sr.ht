import gzip
import json
import os
from collections import OrderedDict
from flask import Blueprint, render_template, request, url_for, abort, redirect
from flask import current_app, send_file
from srht.config import get_origin
from srht.crypto import sign_payload
from srht.database import db
from srht.oauth import current_user, loginrequired
from srht.flask import date_handler, session
from srht.validation import Validation
from tempfile import NamedTemporaryFile
from todosrht.access import get_tracker
from todosrht.trackers import get_recent_users
from todosrht.types import Event, EventType, Ticket, TicketAccess
from todosrht.types import ParticipantType, UserAccess, User
from todosrht.urls import tracker_url
from todosrht.webhooks import UserWebhook
from todosrht.tracker_import import tracker_import

settings = Blueprint("settings", __name__)

def parse_html_perms(short, valid):
    result = 0
    for sub_perm in TicketAccess:
        new_perm = valid.optional("perm_{}_{}".format(short, sub_perm.name))
        if new_perm:
            result |= int(new_perm)
    return result

access_help_map={
    TicketAccess.browse:
        "Permission to view tickets",
    TicketAccess.submit:
        "Permission to submit tickets",
    TicketAccess.comment:
        "Permission to comment on tickets",
    TicketAccess.edit:
        "Permission to edit tickets",
    TicketAccess.triage:
        "Permission to resolve, re-open, or label tickets",
}

@settings.route("/<owner>/<name>/settings/details")
@loginrequired
def details_GET(owner, name):
    tracker, access = get_tracker(owner, name)
    if not tracker:
        abort(404)
    if current_user.id != tracker.owner_id:
        abort(403)
    return render_template("tracker-details.html",
        view="details", tracker=tracker)

@settings.route("/<owner>/<name>/settings/details", methods=["POST"])
@loginrequired
def details_POST(owner, name):
    tracker, access = get_tracker(owner, name)
    if not tracker:
        abort(404)
    if current_user.id != tracker.owner_id:
        abort(403)

    valid = Validation(request)
    desc = valid.optional("tracker_desc", default=tracker.description)
    valid.expect(not desc or len(desc) < 4096,
            "Must be less than 4096 characters",
            field="tracker_desc")
    if not valid.ok:
        return render_template("tracker-details.html",
            tracker=tracker, **valid.kwargs), 400

    tracker.description = desc

    UserWebhook.deliver(UserWebhook.Events.tracker_update,
            tracker.to_dict(),
            UserWebhook.Subscription.user_id == tracker.owner_id)

    db.session.commit()
    return redirect(tracker_url(tracker))


def render_tracker_access(tracker, **kwargs):
    recent_users = get_recent_users(tracker)
    return render_template("tracker-access.html",
        view="access", tracker=tracker, access_type_list=TicketAccess,
        access_help_map=access_help_map, recent_users=recent_users, **kwargs)


@settings.route("/<owner>/<name>/settings/access")
@loginrequired
def access_GET(owner, name):
    tracker, access = get_tracker(owner, name)
    if not tracker:
        abort(404)
    if current_user.id != tracker.owner_id:
        abort(403)
    return render_tracker_access(tracker)

@settings.route("/<owner>/<name>/settings/access", methods=["POST"])
@loginrequired
def access_POST(owner, name):
    tracker, access = get_tracker(owner, name)
    if not tracker:
        abort(404)
    if current_user.id != tracker.owner_id:
        abort(403)

    valid = Validation(request)
    perm_anon = parse_html_perms('anon', valid)
    perm_user = parse_html_perms('user', valid)
    perm_submit = parse_html_perms('submit', valid)

    if not valid.ok:
        return render_tracker_access(tracker, **valid.kwargs), 400

    tracker.default_anonymous_perms = perm_anon
    tracker.default_user_perms = perm_user
    tracker.default_submitter_perms = perm_submit

    UserWebhook.deliver(UserWebhook.Events.tracker_update,
            tracker.to_dict(),
            UserWebhook.Subscription.user_id == tracker.owner_id)

    db.session.commit()
    return redirect(tracker_url(tracker))

@settings.route("/<owner>/<name>/settings/user-access/create", methods=["POST"])
@loginrequired
def user_access_create_POST(owner, name):
    tracker, access = get_tracker(owner, name)
    if not tracker:
        abort(404)
    if current_user.id != tracker.owner_id:
        abort(403)

    valid = Validation(request)
    username = valid.require("username")
    permissions = parse_html_perms("user_access", valid)
    if not valid.ok:
        return render_tracker_access(tracker, **valid.kwargs), 400

    username = username.lstrip("~")
    user = current_app.oauth_service.lookup_user(username)
    valid.expect(user, "User not found.", field="username")
    if not valid.ok:
        return render_tracker_access(tracker, **valid.kwargs), 400

    existing = UserAccess.query.filter_by(user=user, tracker=tracker).count()

    valid.expect(user != tracker.owner,
        "Cannot override tracker owner's permissions.", field="username")
    valid.expect(existing == 0,
        "This user already has custom permissions assigned.", field="username")
    if not valid.ok:
        return render_tracker_access(tracker, **valid.kwargs), 400

    ua = UserAccess(tracker=tracker, user=user, permissions=permissions)
    db.session.add(ua)
    db.session.commit()

    return redirect(url_for("settings.access_GET",
            owner=tracker.owner.canonical_name,
            name=name))

@settings.route("/<owner>/<name>/settings/user-access/<user_id>/delete",
    methods=["POST"])
@loginrequired
def user_access_delete_POST(owner, name, user_id):
    tracker, access = get_tracker(owner, name)
    if not tracker:
        abort(404)
    if current_user.id != tracker.owner_id:
        abort(403)

    UserAccess.query.filter_by(user_id=user_id, tracker_id=tracker.id).delete()
    db.session.commit()

    return redirect(url_for("settings.access_GET",
            owner=tracker.owner.canonical_name,
            name=name))

@settings.route("/<owner>/<name>/settings/delete")
@loginrequired
def delete_GET(owner, name):
    tracker, access = get_tracker(owner, name)
    if not tracker:
        abort(404)
    if current_user.id != tracker.owner_id:
        abort(403)
    return render_template("tracker-delete.html",
        view="delete", tracker=tracker)

@settings.route("/<owner>/<name>/settings/delete", methods=["POST"])
@loginrequired
def delete_POST(owner, name):
    tracker, access = get_tracker(owner, name)
    if not tracker:
        abort(404)
    if current_user.id != tracker.owner_id:
        abort(403)
    session["notice"] = f"{tracker.owner}/{tracker.name} was deleted."
    # SQLAlchemy shits itself on some of our weird constraints/relationships
    # so fuck it, postgres knows what to do here
    tracker_id = tracker.id
    owner_id = tracker.owner_id
    assert isinstance(tracker_id, int)
    db.session.expunge_all()
    db.engine.execute(f"DELETE FROM tracker WHERE id = {tracker_id};")
    db.session.commit()

    UserWebhook.deliver(UserWebhook.Events.tracker_delete,
            { "id": tracker_id },
            UserWebhook.Subscription.user_id == owner_id)

    return redirect(url_for("html.index"))

@settings.route("/<owner>/<name>/settings/import-export")
@loginrequired
def import_export_GET(owner, name):
    tracker, access = get_tracker(owner, name)
    if not tracker:
        abort(404)
    if current_user.id != tracker.owner_id:
        abort(403)
    return render_template("tracker-import-export.html",
        view="import/export", tracker=tracker)

@settings.route("/<owner>/<name>/settings/export", methods=["POST"])
@loginrequired
def export_POST(owner, name):
    tracker, access = get_tracker(owner, name)
    if not tracker:
        abort(404)
    if current_user.id != tracker.owner_id:
        abort(403)

    dump = list()
    tickets = Ticket.query.filter(Ticket.tracker_id == tracker.id).all()
    for ticket in tickets:
        td = ticket.to_dict()
        td["upstream"] = get_origin("todo.sr.ht", external=True)
        if ticket.submitter.participant_type == ParticipantType.user:
            sigdata = OrderedDict({
                "description": ticket.description,
                "ref": ticket.ref(),
                "submitter": ticket.submitter.user.canonical_name,
                "title": ticket.title,
                "upstream": get_origin("todo.sr.ht", external=True),
            })
            sigdata = json.dumps(sigdata)
            signature = sign_payload(sigdata)
            td.update(signature)

        events = Event.query.filter(Event.ticket_id == ticket.id).all()
        if any(events):
            td["events"] = list()
        for event in events:
            ev = event.to_dict()
            ev["upstream"] = get_origin("todo.sr.ht", external=True)
            if (EventType.comment in event.event_type
                    and event.participant.participant_type == ParticipantType.user):
                sigdata = OrderedDict({
                    "comment": event.comment.text,
                    "id": event.id,
                    "ticket": event.ticket.ref(),
                    "user": event.participant.user.canonical_name,
                    "upstream": get_origin("todo.sr.ht", external=True),
                })
                sigdata = json.dumps(sigdata)
                signature = sign_payload(sigdata)
                ev.update(signature)
            td["events"].append(ev)
        dump.append(td)

    dump = json.dumps({
        "owner": tracker.owner.to_dict(),
        "name": tracker.name,
        "labels": [l.to_dict() for l in tracker.labels],
        "tickets": dump,
    }, default=date_handler)
    with NamedTemporaryFile() as ntf:
        ntf.write(gzip.compress(dump.encode()))
        f = open(ntf.name, "rb")

    return send_file(f, as_attachment=True,
            attachment_filename=f"{tracker.owner.username}-{tracker.name}.json.gz",
            mimetype="application/gzip")

@settings.route("/<owner>/<name>/settings/import", methods=["POST"])
@loginrequired
def import_POST(owner, name):
    tracker, access = get_tracker(owner, name)
    if not tracker:
        abort(404)
    if current_user.id != tracker.owner_id:
        abort(403)

    dump = request.files.get("dump")
    valid = Validation(request)
    valid.expect(dump is not None,
            "Tracker dump file is required", field="dump")
    if not valid.ok:
        return render_template("tracker-import-export.html",
            view="import/export", tracker=tracker, **valid.kwargs)

    dump = dump.stream.read()
    dump = gzip.decompress(dump)
    dump = json.loads(dump)
    tracker_import.delay(dump, tracker.id)

    tracker.import_in_progress = True
    db.session.commit()
    return redirect(tracker_url(tracker))
