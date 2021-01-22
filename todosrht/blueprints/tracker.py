from urllib.parse import quote
from flask import Blueprint, render_template, request, url_for, abort, redirect
from todosrht.color import color_from_hex, color_to_hex, get_text_color
from todosrht.color import valid_hex_color_code
from todosrht.access import get_tracker
from todosrht.filters import render_markup
from todosrht.search import apply_search
from todosrht.tickets import get_last_seen_times, get_comment_counts
from todosrht.tickets import get_participant_for_user, submit_ticket
from todosrht.trackers import get_recent_users
from todosrht.types import Event, Label, TicketLabel
from todosrht.types import TicketSubscription, Participant
from todosrht.types import Tracker, Ticket, TicketAccess
from todosrht.urls import tracker_url, ticket_url
from todosrht.webhooks import TrackerWebhook, UserWebhook
from srht.config import cfg
from srht.database import db
from srht.flask import paginate_query, session
from srht.oauth import current_user, loginrequired
from srht.validation import Validation
from sqlalchemy.orm import subqueryload

tracker = Blueprint("tracker", __name__)

smtp_user = cfg("mail", "smtp-user", default=None)
smtp_from = cfg("mail", "smtp-from", default=None)
notify_from = cfg("todo.sr.ht", "notify-from", default=smtp_from)
posting_domain = cfg("todo.sr.ht::mail", "posting-domain")

tracker_subscribe_body = """\
Sending this email will subscribe your email address to {tracker_ref},
in so doing you will start receiving new tickets and all comments for this tracker.

You can unsubscribe at any time by mailing <{tracker_ref}/unsubscribe@""" + \
    posting_domain + ">.\n"

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

    participant = get_participant_for_user(current_user)
    sub = TicketSubscription()
    sub.tracker_id = tracker.id
    sub.participant_id = participant.id
    db.session.add(sub)
    db.session.commit()

    if "create-configure" in valid:
        return redirect(url_for("settings.details_GET",
                owner=current_user.canonical_name,
                name=tracker.name))

    return redirect(tracker_url(tracker))

def return_tracker(tracker, access, **kwargs):
    another = session.get("another") or False
    if another:
        del session["another"]
    is_subscribed = False
    tracker_subscribe = None
    if current_user:
        sub = (TicketSubscription.query
            .join(Participant)
            .filter(TicketSubscription.tracker_id == tracker.id)
            .filter(TicketSubscription.ticket_id == None)
            .filter(Participant.user_id == current_user.id)
        ).one_or_none()
        is_subscribed = bool(sub)
    else:
        subj = quote("Subscribing to " + tracker.ref())
        tracker_subscribe = f"mailto:{tracker.ref()}/subscribe@" + \
            f"{posting_domain}?subject={subj}&body=" + \
            quote(tracker_subscribe_body.format(tracker_ref=tracker.ref()))

    tickets = (Ticket.query
        .filter(Ticket.tracker_id == tracker.id)
        .options(subqueryload(Ticket.labels))
        .options(subqueryload(Ticket.submitter))
        .order_by(Ticket.updated.desc()))

    try:
        terms = request.args.get("search")
        tickets = apply_search(tickets, terms, current_user)
    except ValueError as e:
        kwargs["search_error"] = str(e)

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
            tracker_subscribe=tracker_subscribe, **pagination, **kwargs)

@tracker.route("/<owner>/<name>")
def tracker_GET(owner, name):
    tracker, access = get_tracker(owner, name)
    if not tracker:
        abort(404)

    # Populate title and description if given as URL parameters
    kwargs = {
        "title": request.args.get("title"),
        "description": request.args.get("description"),
    }

    return return_tracker(tracker, access, **kwargs)

@tracker.route("/<owner>/<name>/enable_notifications", methods=["POST"])
@loginrequired
def enable_notifications(owner, name):
    tracker, access = get_tracker(owner, name)
    if not tracker:
        abort(404)

    participant = get_participant_for_user(current_user)
    sub = (TicketSubscription.query
        .filter(TicketSubscription.tracker_id == tracker.id)
        .filter(TicketSubscription.ticket_id == None)
        .filter(TicketSubscription.participant_id == participant.id)
    ).one_or_none()

    if sub:
        return redirect(tracker_url(tracker))

    sub = TicketSubscription()
    sub.tracker_id = tracker.id
    sub.participant_id = participant.id
    db.session.add(sub)
    db.session.commit()
    return redirect(tracker_url(tracker))

@tracker.route("/<owner>/<name>/disable_notifications", methods=["POST"])
@loginrequired
def disable_notifications(owner, name):
    tracker, access = get_tracker(owner, name)
    if not tracker:
        abort(404)

    participant = get_participant_for_user(current_user)
    sub = (TicketSubscription.query
        .filter(TicketSubscription.tracker_id == tracker.id)
        .filter(TicketSubscription.ticket_id == None)
        .filter(TicketSubscription.participant_id == participant.id)
    ).one_or_none()

    if not sub:
        return redirect(tracker_url(tracker))

    db.session.delete(sub)
    db.session.commit()
    return redirect(tracker_url(tracker))

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

    if "preview" in request.form:
        preview = render_markup(tracker, desc or "")
        return return_tracker(tracker, access,
                rendered_preview=preview, **valid.kwargs), 200

    # TODO: Handle unique constraint failure (contention) and retry?
    participant = get_participant_for_user(current_user)
    ticket = submit_ticket(tracker, participant, title, desc)

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
def tracker_labels_GET(owner, name):
    tracker, access = get_tracker(owner, name)
    if not tracker:
        abort(404)

    is_owner = current_user and current_user.id == tracker.owner_id
    return render_template("tracker-labels.html",
        tracker=tracker, access=access, is_owner=is_owner)

def validate_label(request):
    valid = Validation(request)
    name = valid.require("name")
    color = valid.require("color")
    if not valid.ok:
        return None, valid

    valid.expect(2 <= len(name) <= 50,
            "Must be between 2 and 50 characters", field="name")
    valid.expect(valid_hex_color_code(color),
            "Invalid hex color code", field="color")
    if not valid.ok:
        return None, valid

    # Determine a foreground color to use
    color_rgb = color_from_hex(color)
    text_color_rgb = get_text_color(color_rgb)
    text_color = color_to_hex(text_color_rgb)

    label = dict(name=name, color=color, text_color=text_color)
    return label, valid


@tracker.route("/<owner>/<name>/labels", methods=["POST"])
@loginrequired
def tracker_labels_POST(owner, name):
    tracker, access = get_tracker(owner, name)
    is_owner = current_user.id == tracker.owner_id
    if not tracker:
        abort(404)
    if not is_owner:
        abort(403)

    data, valid = validate_label(request)
    if not valid.ok:
        return render_template("tracker-labels.html",
            tracker=tracker, access=access, is_owner=is_owner,
            **valid.kwargs), 400

    existing_label = Label.query.filter_by(
            tracker=tracker, name=data["name"]).one_or_none()
    valid.expect(not existing_label,
            "A label with this name already exists", field="name")
    if not valid.ok:
        return render_template("tracker-labels.html",
            tracker=tracker, access=access, is_owner=is_owner,
            **valid.kwargs), 400

    label = Label(tracker=tracker, **data)
    db.session.add(label)
    db.session.commit()

    TrackerWebhook.deliver(TrackerWebhook.Events.label_create,
            label.to_dict(),
            TrackerWebhook.Subscription.tracker_id == tracker.id)
    return redirect(url_for(".tracker_labels_GET", owner=owner, name=name))

@tracker.route("/<owner>/<name>/labels/<path:label_name>")
@loginrequired
def label_edit_GET(owner, name, label_name):
    tracker, access = get_tracker(owner, name)
    if not tracker:
        abort(404)
    if current_user.id != tracker.owner_id:
        abort(403)

    label = Label.query.filter_by(tracker=tracker, name=label_name).first()
    if not label:
        abort(404)

    return render_template("tracker-label-edit.html",
        tracker=tracker, access=access, label=label)

@tracker.route("/<owner>/<name>/labels/<path:label_name>", methods=["POST"])
@loginrequired
def label_edit_POST(owner, name, label_name):
    tracker, access = get_tracker(owner, name)
    if not tracker:
        abort(404)
    if current_user.id != tracker.owner_id:
        abort(403)

    label = Label.query.filter_by(
        tracker=tracker, name=label_name).one_or_none()
    if not label:
        abort(404)

    data, valid = validate_label(request)
    if not valid.ok:
        return render_template("tracker-label-edit.html",
            tracker=tracker, access=access, label=label, **valid.kwargs), 400

    existing_label = Label.query.filter_by(
            tracker=tracker, name=data["name"]).one_or_none()
    valid.expect(not existing_label or existing_label == label,
            "A label with this name already exists", field="name")
    if not valid.ok:
        return render_template("tracker-label-edit.html",
            tracker=tracker, access=access, **valid.kwargs), 400

    label.name = data["name"]
    label.color = data["color"]
    label.text_color = data["text_color"]
    db.session.commit()

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
