from flask import Blueprint, abort, request
from srht.api import paginated_response
from srht.database import db
from srht.oauth import oauth, current_token
from srht.validation import Validation
from todosrht.access import get_tracker
from todosrht.blueprints.api import get_user
from todosrht.tickets import get_participant_for_user
from todosrht.types import Label, Tracker, TicketAccess, TicketSubscription
from todosrht.webhooks import UserWebhook, TrackerWebhook

trackers = Blueprint("api_trackers", __name__)

@trackers.route("/api/user/<username>/trackers")
@trackers.route("/api/trackers", defaults={"username": None})
@oauth("trackers:read")
def user_trackers_GET(username):
    user = get_user(username)
    trackers = Tracker.query.filter(Tracker.owner_id == user.id)
    if current_token.user_id != user.id:
        # TODO: proper ACLs
        trackers = trackers.filter(Tracker.default_access > 0)
    return paginated_response(Tracker.id, trackers)

@trackers.route("/api/trackers", methods=["POST"])
@oauth("trackers:write")
def user_trackers_POST():
    user = current_token.user
    tracker, valid = Tracker.create_from_request(request, user)
    if not valid.ok:
        return valid.response
    db.session.add(tracker)
    db.session.commit()
    UserWebhook.deliver(UserWebhook.Events.tracker_create,
            tracker.to_dict(),
            UserWebhook.Subscription.user_id == tracker.owner_id)

    # Auto-subscribe the owner
    sub = TicketSubscription()
    participant = get_participant_for_user(user)
    sub.tracker_id = tracker.id
    sub.participant_id = participant.id
    db.session.add(sub)
    db.session.commit()

    return tracker.to_dict(), 201

@trackers.route("/api/user/<username>/trackers/<tracker_name>")
@trackers.route("/api/trackers/<tracker_name>", defaults={"username": None})
@oauth("trackers:read")
def user_tracker_by_name_GET(username, tracker_name):
    user = get_user(username)
    tracker, access = get_tracker(user, tracker_name, user=current_token.user)
    if not tracker:
        abort(404)
    if not TicketAccess.browse in access:
        abort(401)
    return tracker.to_dict()

def _webhook_filters(query, username, tracker_name):
    user = get_user(username)
    tracker, access = get_tracker(user, tracker_name, user=current_token.user)
    if not tracker:
        abort(404)
    if not TicketAccess.browse in access:
        abort(401)
    return query.filter(TrackerWebhook.Subscription.tracker_id == tracker.id)

def _webhook_create(sub, valid, username, tracker_name):
    if current_token.token_partial != "internal":
        abort(401)
    user = get_user(username)
    tracker, access = get_tracker(user, tracker_name, user=current_token.user)
    if not tracker:
        abort(404)
    if not TicketAccess.browse in access:
        abort(401)
    sub.tracker_id = tracker.id
    return sub

TrackerWebhook.api_routes(trackers,
        "/api/user/<username>/trackers/<tracker_name>",
        filters=_webhook_filters, create=_webhook_create)

@trackers.route("/api/user/<username>/trackers/<tracker_name>", methods=["PUT"])
@trackers.route("/api/trackers/<tracker_name>",
        defaults={"username": None}, methods=["PUT"])
@oauth("trackers:write")
def user_tracker_by_name_PUT(username, tracker_name):
    user = get_user(username)
    tracker, access = get_tracker(user, tracker_name, user=current_token.user)
    if not tracker:
        abort(404)
    if tracker.owner_id != current_token.user_id:
        abort(401)
    valid = Validation(request)
    tracker.update(valid)
    if not valid.ok:
        return valid.response
    db.session.commit()
    UserWebhook.deliver(UserWebhook.Events.tracker_update,
            tracker.to_dict(),
            UserWebhook.Subscription.user_id == tracker.owner_id)
    return tracker.to_dict()

@trackers.route("/api/user/<username>/trackers/<tracker_name>",
        methods=["DELETE"])
@trackers.route("/api/trackers/<tracker_name>",
        defaults={"username": None}, methods=["DELETE"])
@oauth("trackers:write")
def user_tracker_by_name_DELETE(username, tracker_name):
    user = get_user(username)
    tracker, access = get_tracker(user, tracker_name, user=current_token.user)
    if not tracker:
        abort(404)
    if tracker.owner_id != current_token.user_id:
        abort(401)
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
    return {}, 204

@trackers.route("/api/user/<username>/trackers/<tracker_name>/labels")
@trackers.route("/api/trackers/<tracker_name>/labels", defaults={"username": None})
@oauth("trackers:read")
def tracker_labels_GET(username, tracker_name):
    user = get_user(username)
    tracker, access = get_tracker(user, tracker_name, user=current_token.user)
    if not tracker:
        abort(404)
    if not TicketAccess.browse in access:
        abort(401)
    labels = Label.query.filter(Label.tracker_id == tracker.id)
    return paginated_response(Label.id, labels)
