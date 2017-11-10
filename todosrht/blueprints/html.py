from flask import Blueprint, render_template
from flask_login import current_user
from todosrht.types import Tracker, Event, EventNotification, EventType
from todosrht.types import User
from srht.config import cfg
import requests

html = Blueprint('html', __name__)

meta_uri = cfg("network", "meta")

@html.route("/")
def index():
    if not current_user:
        return render_template("index.html")
    # TODO: pagination?
    trackers = (Tracker.query
            .filter(Tracker.owner_id == current_user.id)
            .order_by(Tracker.updated.desc())).all()
    events = [e.event for e in (EventNotification.query
            .filter(EventNotification.user_id == current_user.id)
            .order_by(EventNotification.created.desc())
            .limit(10)).all()]
    return render_template("dashboard.html",
            trackers=trackers,
            tracker_list_msg="Your Trackers",
            events=events,
            EventType=EventType)

@html.route("/~<username>")
def user_GET(username):
    print(username)
    user = User.query.filter(User.username == username.lower()).first()
    if not user:
        abort(404)
    trackers = (Tracker.query
            .filter(Tracker.owner_id == current_user.id)
            .order_by(Tracker.updated.desc())).all()
    events = (Event.query
            .filter(Event.user_id == user.id)
            .order_by(Event.created.desc())
            .limit(10)).all()
    r = requests.get(meta_uri + "/api/user/profile", headers={
        "Authorization": "token " + user.oauth_token
    }) # TODO: cache this
    if r.status_code == 200:
        profile = r.json()
    else:
        profile = None
    return render_template("dashboard.html",
            user=user,
            profile=profile,
            trackers=trackers,
            tracker_list_msg="Trackers".format(user.username),
            events=events,
            EventType=EventType)
