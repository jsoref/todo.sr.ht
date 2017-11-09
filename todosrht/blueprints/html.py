from flask import Blueprint, render_template
from flask_login import current_user
from todosrht.types import Tracker

html = Blueprint('html', __name__)

@html.route("/")
def index():
    if not current_user:
        return render_template("index.html")
    # TODO: pagination?
    your_trackers = (Tracker.query
            .filter(Tracker.owner_id == current_user.id)
            .order_by(Tracker.updated.desc())).all()
    return render_template("dashboard.html",
            your_trackers=your_trackers)
