from flask import Blueprint, current_app, abort, request
from srht.api import paginated_response
from srht.database import db
from srht.graphql import exec_gql
from srht.oauth import oauth, current_token
from srht.validation import Validation
from todosrht.access import get_tracker
from todosrht.blueprints.api import get_user
from todosrht.tickets import get_participant_for_user
from todosrht.types import Label, Tracker, TicketAccess, TicketSubscription
from todosrht.webhooks import TrackerWebhook

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
    valid = Validation(request)
    name = valid.require("name", friendly_name="Name")
    description = valid.optional("description")
    visibility = valid.require("visibility")
    if not valid.ok:
        return valid.response

    resp = exec_gql(current_app.site, """
        mutation CreateTracker($name: String!, $description: String, $visibility: Visibility!) {
            createTracker(name: $name, description: $description, visibility: $visibility) {
                id
                created
                updated
                owner {
                    canonical_name: canonicalName
                    ... on User {
                        name: username
                    }
                }
                name
                description
                defaultACL {
                    browse
                    submit
                    comment
                    edit
                    triage
                }
                visibility
            }
        }
    """, user=user, valid=valid, name=name, description=description, visibility=visibility)

    if not valid.ok:
        return valid.response

    resp = resp["createTracker"]

    # Build default_access list
    resp["default_access"] = [
        key for key in [
            "browse", "submit", "comment", "edit", "triage"
        ] if resp["defaultACL"][key]
    ]
    del resp["defaultACL"]

    return resp, 201

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
    rewrite = lambda value: None if value == "" else value
    input = {
        key: rewrite(valid.source[key]) for key in [
            "description"
        ] if valid.source.get(key) is not None
    }

    resp = exec_gql(current_app.site, """
        mutation UpdateTracker($id: Int!, $input: TrackerInput!) {
            updateTracker(id: $id, input: $input) {
                id
                created
                updated
                owner {
                    canonical_name: canonicalName
                    ... on User {
                        name: username
                    }
                }
                name
                description
                defaultACL {
                    browse
                    submit
                    comment
                    edit
                    triage
                }
                visibility
            }
        }
    """, user=user, valid=valid, id=tracker.id, input=input)

    if not valid.ok:
        return valid.response

    resp = resp["updateTracker"]

    # Build default_access list
    resp["default_access"] = [
        key for key in [
            "browse", "submit", "comment", "edit", "triage"
        ] if resp["defaultACL"][key]
    ]
    del resp["defaultACL"]

    return resp

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
    exec_gql(current_app.site, """
    mutation DeleteTracker($id: Int!) {
        deleteTracker(id: $id) { id }
    }
    """, user=user, id=tracker.id);
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
