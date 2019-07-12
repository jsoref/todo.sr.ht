from flask import Blueprint, render_template, request, abort
from flask_login import current_user
from todosrht.access import get_tracker, get_access
from todosrht.types import Tracker, Ticket, Event, EventNotification, EventType
from todosrht.types import User
from srht.config import cfg
from srht.flask import paginate_query, session
from sqlalchemy import and_, or_

html = Blueprint('html', __name__)

def filter_authorized_events(events):
    events = (events
        .join(Ticket, Ticket.id == Event.ticket_id)
        .join(Tracker, Tracker.id == Ticket.tracker_id))
    if current_user:
        events = (events.filter(
            or_(
                and_(
                    Ticket.submitter_perms != None,
                    Ticket.submitter_id == current_user.id,
                    Ticket.submitter_perms > 0),
                and_(
                    Ticket.user_perms != None,
                    Ticket.user_perms > 0),
                and_(
                    Ticket.anonymous_perms != None,
                    Ticket.anonymous_perms > 0),
                and_(
                    Ticket.submitter_perms == None,
                    Ticket.submitter_id == current_user.id,
                    Tracker.default_submitter_perms > 0),
                and_(
                    Ticket.user_perms == None,
                    Tracker.default_user_perms > 0),
                and_(
                    Ticket.anonymous_perms == None,
                    Tracker.default_anonymous_perms > 0))))
    else:
        events = (events.filter(
            or_(
                and_(
                    Ticket.anonymous_perms != None,
                    Ticket.anonymous_perms > 0),
                and_(
                    Ticket.anonymous_perms == None,
                    Tracker.default_anonymous_perms > 0))))
    return events

@html.route("/")
def index():
    if not current_user:
        return render_template("index.html")
    trackers = (Tracker.query
        .filter(Tracker.owner_id == current_user.id)
        .order_by(Tracker.updated.desc())
    )
    limit_trackers = 10
    total_trackers = trackers.count()
    trackers = trackers.limit(limit_trackers).all()

    events = (Event.query
            .join(EventNotification)
            .filter(EventNotification.user_id == current_user.id)
            .order_by(Event.created.desc()))
    events = events.limit(10).all()

    notice = session.get("notice")
    if notice:
        del session["notice"]

    return render_template("dashboard.html",
        trackers=trackers, notice=notice,
        tracker_list_msg="Your Trackers",
        more_trackers=total_trackers > limit_trackers,
        events=events, EventType=EventType)

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
    limit_trackers = 10
    total_trackers = trackers.count()
    trackers = (trackers
        .order_by(Tracker.updated.desc())
        .limit(limit_trackers)
    ).all()

    # TODO: Join on stuff the user has explicitly been granted access to
    events = (Event.query
            .filter(Event.user_id == user.id)
            .order_by(Event.created.desc()))
    if not current_user or current_user.id != user.id:
        events = filter_authorized_events(events)
    events = events.limit(10).all()

    return render_template("dashboard.html",
        user=user,
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

    return render_template("trackers.html",
            user=user, trackers=trackers, search=search, **pagination)
