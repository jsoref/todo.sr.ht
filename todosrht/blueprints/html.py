from flask import Blueprint, render_template

html = Blueprint('html', __name__)

@html.route("/")
def index():
    return render_template("index.html")
