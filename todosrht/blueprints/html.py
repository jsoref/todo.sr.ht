from flask import Blueprint, render_template
from flask_login import current_user
from todosrht.access import get_tracker, get_access
from todosrht.types import Tracker, Event, EventNotification, EventType
from todosrht.types import User
from srht.config import cfg
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
    # TODO: pagination?
    trackers = (Tracker.query
            .filter(Tracker.owner_id == current_user.id)
            .order_by(Tracker.updated.desc())).all()
    events = collect_events(current_user, 10)
    return render_template("dashboard.html",
        trackers=trackers,
        tracker_list_msg="Your Trackers",
        events=events,
        EventType=EventType)

@html.route("/~<username>")
def user_GET(username):
    user = User.query.filter(User.username == username.lower()).first()
    if not user:
        abort(404)
    trackers, _ = get_tracker(username, None)
    events = collect_events(user, 10)
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
        events=events,
        EventType=EventType)
