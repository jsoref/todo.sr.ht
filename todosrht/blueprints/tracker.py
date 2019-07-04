from flask import Blueprint, render_template, request, url_for, abort, redirect
from flask import session
from flask_login import current_user
from todosrht import color
from todosrht.access import get_tracker
from todosrht.search import apply_search
from todosrht.tickets import get_last_seen_times, get_comment_counts
from todosrht.tickets import submit_ticket
from todosrht.types import TicketSubscription, User
from todosrht.types import Event, UserAccess
from todosrht.types import Tracker, Ticket, TicketAccess
from todosrht.types import Label, TicketLabel
from todosrht.urls import tracker_url, ticket_url
from todosrht.webhooks import TrackerWebhook, UserWebhook
from srht.config import cfg
from srht.database import db
from srht.flask import paginate_query, loginrequired
from srht.validation import Validation
from sqlalchemy.orm import subqueryload

tracker = Blueprint("tracker", __name__)

smtp_user = cfg("mail", "smtp-user", default=None)
smtp_from = cfg("mail", "smtp-from", default=None)
notify_from = cfg("todo.sr.ht", "notify-from", default=smtp_from)

@tracker.route("/tracker/create")
@loginrequired
def create_GET():
    return render_template("tracker-create.html")

@tracker.route("/tracker/create", methods=["POST"])
@loginrequired
def create_POST():
    tracker, valid = Tracker.create_from_request(request, current_user)
    if not valid.ok:
        return render_template("tracker-create.html", **valid.kwargs), 400

    db.session.add(tracker)
    db.session.flush()

    UserWebhook.deliver(UserWebhook.Events.tracker_create,
            tracker.to_dict(),
            UserWebhook.Subscription.user_id == tracker.owner_id)

    sub = TicketSubscription()
    sub.tracker_id = tracker.id
    sub.user_id = current_user.id
    db.session.add(sub)
    db.session.commit()

    if "create-configure" in valid:
        return redirect(url_for(".settings_details_GET",
                owner=current_user.username,
                name=tracker.name))

    return redirect(tracker_url(tracker))

def return_tracker(tracker, access, **kwargs):
    another = session.get("another") or False
    if another:
        del session["another"]
    is_subscribed = False
    if current_user:
        sub = (TicketSubscription.query
            .filter(TicketSubscription.tracker_id == tracker.id)
            .filter(TicketSubscription.ticket_id == None)
            .filter(TicketSubscription.user_id == current_user.id)
        ).one_or_none()
        is_subscribed = bool(sub)

    tickets = (Ticket.query
        .filter(Ticket.tracker_id == tracker.id)
        .options(subqueryload(Ticket.labels))
        .options(subqueryload(Ticket.submitter))
        .order_by(Ticket.updated.desc()))

    terms = request.args.get("search")
    tickets = apply_search(tickets, terms, tracker, current_user)
    tickets, pagination = paginate_query(tickets, results_per_page=25)

    # Find which tickets were seen by the user since last update
    seen_ticket_ids = []
    if current_user:
        seen_times = get_last_seen_times(current_user, tickets)
        seen_ticket_ids = [t.id for t in tickets
            if t.id in seen_times and seen_times[t.id] >= t.updated]

    # Preload comment counts
    comment_counts = get_comment_counts(tickets)

    if "another" in kwargs:
        another = kwargs["another"]
        del kwargs["another"]

    return render_template("tracker.html",
            tracker=tracker, another=another, tickets=tickets,
            access=access, is_subscribed=is_subscribed, search=terms,
            comment_counts=comment_counts, seen_ticket_ids=seen_ticket_ids,
            **pagination, **kwargs)

@tracker.route("/<owner>/<name>")
def tracker_GET(owner, name):
    tracker, access = get_tracker(owner, name)
    if not tracker:
        abort(404)
    return return_tracker(tracker, access)

@tracker.route("/<owner>/<name>/enable_notifications", methods=["POST"])
@loginrequired
def enable_notifications(owner, name):
    tracker, access = get_tracker(owner, name)
    if not tracker:
        abort(404)

    sub = (TicketSubscription.query
        .filter(TicketSubscription.tracker_id == tracker.id)
        .filter(TicketSubscription.ticket_id == None)
        .filter(TicketSubscription.user_id == current_user.id)
    ).one_or_none()

    if sub:
        return redirect(tracker_url(tracker))

    sub = TicketSubscription()
    sub.tracker_id = tracker.id
    sub.user_id = current_user.id
    db.session.add(sub)
    db.session.commit()
    return redirect(tracker_url(tracker))

@tracker.route("/<owner>/<name>/disable_notifications", methods=["POST"])
@loginrequired
def disable_notifications(owner, name):
    tracker, access = get_tracker(owner, name)
    if not tracker:
        abort(404)

    sub = (TicketSubscription.query
        .filter(TicketSubscription.tracker_id == tracker.id)
        .filter(TicketSubscription.ticket_id == None)
        .filter(TicketSubscription.user_id == current_user.id)
    ).one_or_none()

    if not sub:
        return redirect(tracker_url(tracker))

    db.session.delete(sub)
    db.session.commit()
    return redirect(tracker_url(tracker))

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

@tracker.route("/<owner>/<name>/settings/details")
@loginrequired
def settings_details_GET(owner, name):
    tracker, access = get_tracker(owner, name)
    if not tracker:
        abort(404)
    if current_user.id != tracker.owner_id:
        abort(403)
    return render_template("tracker-details.html",
        view="details", tracker=tracker)

@tracker.route("/<owner>/<name>/settings/details", methods=["POST"])
@loginrequired
def settings_details_POST(owner, name):
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
    return render_template("tracker-access.html",
        view="access", tracker=tracker, access_type_list=TicketAccess,
        access_help_map=access_help_map, **kwargs)


@tracker.route("/<owner>/<name>/settings/access")
@loginrequired
def settings_access_GET(owner, name):
    tracker, access = get_tracker(owner, name)
    if not tracker:
        abort(404)
    if current_user.id != tracker.owner_id:
        abort(403)
    return render_tracker_access(tracker)

@tracker.route("/<owner>/<name>/settings/access", methods=["POST"])
@loginrequired
def settings_access_POST(owner, name):
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

@tracker.route("/<owner>/<name>/settings/user-access/create", methods=["POST"])
@loginrequired
def settings_user_access_create_POST(owner, name):
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
    user = User.query.filter_by(username=username).one_or_none()
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

    return redirect(url_for("tracker.settings_access_GET",
            owner=tracker.owner.canonical_name,
            name=name))

@tracker.route("/<owner>/<name>/settings/user-access/<user_id>/delete",
    methods=["POST"])
@loginrequired
def settings_user_access_delete_POST(owner, name, user_id):
    tracker, access = get_tracker(owner, name)
    if not tracker:
        abort(404)
    if current_user.id != tracker.owner_id:
        abort(403)

    UserAccess.query.filter_by(user_id=user_id, tracker_id=tracker.id).delete()
    db.session.commit()

    return redirect(url_for("tracker.settings_access_GET",
            owner=tracker.owner.canonical_name,
            name=name))

@tracker.route("/<owner>/<name>/settings/delete")
@loginrequired
def settings_delete_GET(owner, name):
    tracker, access = get_tracker(owner, name)
    if not tracker:
        abort(404)
    if current_user.id != tracker.owner_id:
        abort(403)
    return render_template("tracker-delete.html",
        view="delete", tracker=tracker)

@tracker.route("/<owner>/<name>/settings/delete", methods=["POST"])
@loginrequired
def settings_delete_POST(owner, name):
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

@tracker.route("/<owner>/<name>/submit", methods=["POST"])
@loginrequired
def tracker_submit_POST(owner, name):
    tracker, access = get_tracker(owner, name, True)
    if not tracker:
        abort(404)
    if not TicketAccess.submit in access:
        abort(403)

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
        db.session.commit() # Unlock tracker row
        return return_tracker(tracker, access, **valid.kwargs), 400

    # TODO: Handle unique constraint failure (contention) and retry?
    ticket = submit_ticket(tracker, current_user, title, desc)

    UserWebhook.deliver(UserWebhook.Events.ticket_create,
            ticket.to_dict(),
            UserWebhook.Subscription.user_id == current_user.id)
    TrackerWebhook.deliver(TrackerWebhook.Events.ticket_create,
            ticket.to_dict(),
            TrackerWebhook.Subscription.tracker_id == tracker.id)

    if another:
        session["another"] = True
        return redirect(url_for(".tracker_GET",
                owner=tracker.owner.canonical_name,
                name=name))
    else:
        return redirect(ticket_url(ticket))

@tracker.route("/<owner>/<name>/labels")
@loginrequired
def tracker_labels_GET(owner, name):
    tracker, access = get_tracker(owner, name)
    is_owner = current_user.id == tracker.owner_id
    if not tracker:
        abort(404)

    return render_template("tracker-labels.html",
        tracker=tracker, access=access, is_owner=is_owner)

@tracker.route("/<owner>/<name>/labels", methods=["POST"])
@loginrequired
def tracker_labels_POST(owner, name):
    tracker, access = get_tracker(owner, name)
    is_owner = current_user.id == tracker.owner_id
    if not tracker:
        abort(404)
    if not is_owner:
        abort(403)

    valid = Validation(request)
    label_name = valid.require("name")
    label_color = valid.require("color")
    if not valid.ok:
        return render_template("tracker-labels.html",
            tracker=tracker, access=access, is_owner=is_owner,
            **valid.kwargs), 400

    valid.expect(2 < len(label_name) < 50,
            "Must be between 2 and 50 characters", field="name")
    valid.expect(color.valid_hex_color_code(label_color),
            "Invalid hex color code", field="color")
    if not valid.ok:
        return render_template("tracker-labels.html",
            tracker=tracker, access=access, is_owner=is_owner,
            **valid.kwargs), 400

    existing_label = (Label.query
            .filter(Label.tracker_id == tracker.id)
            .filter(Label.name == label_name)).first()
    valid.expect(not existing_label,
            "A label with this name already exists", field="name")
    if not valid.ok:
        return render_template("tracker-labels.html",
            tracker=tracker, access=access, is_owner=is_owner,
            **valid.kwargs), 400

    # Determine a foreground color to use
    label_color_rgb = color.color_from_hex(label_color)
    text_color_rgb = color.get_text_color(label_color_rgb)
    text_color = color.color_to_hex(text_color_rgb)

    label = Label()
    label.tracker_id = tracker.id
    label.name = label_name
    label.color = label_color
    label.text_color = text_color
    db.session.add(label)
    db.session.commit()

    TrackerWebhook.deliver(TrackerWebhook.Events.label_create,
            label.to_dict(),
            TrackerWebhook.Subscription.tracker_id == tracker.id)
    return redirect(url_for(".tracker_labels_GET", owner=owner, name=name))

@tracker.route("/<owner>/<name>/labels/<int:label_id>/delete", methods=["POST"])
@loginrequired
def delete_label(owner, name, label_id):
    tracker, access = get_tracker(owner, name)
    if not tracker:
        abort(404)
    if current_user.id != tracker.owner_id:
        abort(403)

    label = (Label.query
            .filter(Label.tracker_id == tracker.id)
            .filter(Label.id == label_id)).first()

    if not label:
        abort(404)

    # Remove label from any linked tickets and related events
    TicketLabel.query.filter(TicketLabel.label_id == label.id).delete()
    Event.query.filter(Event.label_id == label.id).delete()

    label_id = label.id
    db.session.delete(label)
    db.session.commit()

    TrackerWebhook.deliver(TrackerWebhook.Events.label_delete,
            { "id": label_id },
            TrackerWebhook.Subscription.tracker_id == tracker.id)
    return redirect(url_for(".tracker_labels_GET", owner=owner, name=name))
