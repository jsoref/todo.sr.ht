from flask import Blueprint, render_template
from flask_login import current_user
from todosrht.types import Tracker, Event, EventNotification, EventType
from todosrht.types import User

html = Blueprint('html', __name__)

@html.route("/")
def index():
    if not current_user:
        return render_template("index.html")
    # TODO: pagination?
    your_trackers = (Tracker.query
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
    return render_template("dashboard.html",
            trackers=trackers,
            tracker_list_msg="{}'s Trackers".format(user.username),
            events=events,
            EventType=EventType)
