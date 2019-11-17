import pkg_resources
from flask import abort
from srht.flask import csrf_bypass
from srht.oauth import current_token, oauth
from todosrht.types import User
from todosrht.webhooks import UserWebhook

def get_user(username):
    user = None
    if username == None:
        user = current_token.user
    elif username.startswith("~"):
        user = User.query.filter(User.username == username[1:]).one_or_none()
    if not user:
        abort(404)
    return user

def register_api(app):
    from todosrht.blueprints.api.trackers import trackers
    from todosrht.blueprints.api.tickets import tickets

    trackers = csrf_bypass(trackers)
    tickets = csrf_bypass(tickets)

    app.register_blueprint(trackers)
    app.register_blueprint(tickets)

    @app.route("/api/version")
    def version():
        try:
            dist = pkg_resources.get_distribution("todosrht")
            return { "version": dist.version }
        except:
            return { "version": "unknown" }

    @app.route("/api/user/<username>")
    @app.route("/api/user", defaults={"username": None})
    @oauth(None)
    def user_GET(username):
        if username == None:
            return current_token.user.to_dict()
        return get_user(username).to_dict()

    UserWebhook.api_routes(app, "/api/user")
