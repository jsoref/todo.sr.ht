from flask import Blueprint, render_template, request
from flask_login import current_user
from todosrht.access import get_tracker, get_access
from todosrht.types import Tracker, Event, EventNotification, EventType
from todosrht.types import User
from srht.config import cfg
from srht.flask import paginate_query
from sqlalchemy import or_
import requests

html = Blueprint('html', __name__)

meta_uri = cfg("network", "meta")

def collect_events(target, count):
    events = []
    for e in (EventNotification.query
            .filter(EventNotification.user_id == target.id)
            .order_by(EventNotification.created.desc())):
        ticket = e.event.ticket
        tracker = ticket.tracker
        if get_access(tracker, ticket):
            events.append(e.event)
        if len(events) >= count:
            break
    return events

@html.route("/")
def index():
    if not current_user:
        return render_template("index.html")
    trackers = (Tracker.query
        .filter(Tracker.owner_id == current_user.id)
        .order_by(Tracker.updated.desc())
    )
    limit_trackers = 5
    total_trackers = trackers.count()
    trackers = trackers.limit(limit_trackers).all()

    events = collect_events(current_user, 10)

    return render_template("dashboard.html",
        trackers=trackers,
        tracker_list_msg="Your Trackers",
        more_trackers=total_trackers > limit_trackers,
        events=events,
        EventType=EventType)

@html.route("/~<username>")
def user_GET(username):
    user = User.query.filter(User.username == username.lower()).first()
    if not user:
        abort(404)

    trackers = Tracker.query.filter(Tracker.owner_id == user.id)
    if current_user and current_user != user:
        trackers = trackers.filter(Tracker.default_user_perms > 0)
    elif not current_user:
        trackers = trackers.filter(Tracker.default_anonymous_perms > 0)
    limit_trackers = 5
    total_trackers = trackers.count()
    trackers = (trackers
        .order_by(Tracker.updated.desc())
        .limit(limit_trackers)
    ).all()

    events = collect_events(user, 15)

    r = requests.get(meta_uri + "/api/user/profile", headers={
        "Authorization": "token " + user.oauth_token
    }) # TODO: cache this
    if r.status_code == 200:
        profile = r.json()
    else:
        profile = dict()

    return render_template("dashboard.html",
        user=user,
        profile=profile,
        trackers=trackers,
        tracker_list_msg="Trackers",
        more_trackers=total_trackers > limit_trackers,
        events=events,
        EventType=EventType)

@html.route("/trackers/~<username>")
def trackers_for_user(username):
    user = User.query.filter(User.username == username.lower()).first()
    if not user:
        abort(404)

    trackers = Tracker.query.filter(Tracker.owner_id == user.id)
    if current_user and current_user != user:
        trackers = trackers.filter(Tracker.default_user_perms > 0)
    elif not current_user:
        trackers = trackers.filter(Tracker.default_anonymous_perms > 0)

    search = request.args.get("search")
    if search:
        trackers = trackers.filter(or_(
            Tracker.name.ilike("%" + search + "%"),
            Tracker.description.ilike("%" + search + "%")))

    trackers = trackers.order_by(Tracker.updated.desc())
    trackers, pagination = paginate_query(trackers)

    r = requests.get(meta_uri + "/api/user/profile", headers={
        "Authorization": "token " + user.oauth_token
    }) # TODO: cache this
    if r.status_code == 200:
        profile = r.json()
    else:
        profile = dict()

    return render_template("trackers.html",
            profile=profile, trackers=trackers, search=search, **pagination)
