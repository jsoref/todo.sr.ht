import re

from jinja2.utils import Markup, escape
from srht.flask import icon, csrf_token
from srht.markdown import markdown
from todosrht import urls
from todosrht.tickets import find_mentioned_users, find_mentioned_tickets
from todosrht.tickets import TICKET_MENTION_PATTERN, USER_MENTION_PATTERN


def render_comment(comment):
    users = find_mentioned_users(comment.text)
    tickets = find_mentioned_tickets(comment.ticket.tracker, comment.text)

    users_map = {str(u): u for u in users}
    tickets_map = {str(t.scoped_id): t for t in tickets}

    def urlize_user(match):
        username = match.group(0)
        if username in users_map:
            url = urls.user_url(users_map[username])
            return f'<a href="{url}">{escape(username)}</a>'

        return username

    def urlize_ticket(match):
        scoped_id = match.group(1)
        if scoped_id in tickets_map:
            ticket = tickets_map[scoped_id]
            url = urls.ticket_url(ticket)
            title = escape(f"{ticket.ref()}: {ticket.title}")
            return f'<a href="{url}" title="{title}">#{scoped_id}</a>'

        return match.group(0)

    # Replace ticket and username mentions with linked version
    text = comment.text
    text = re.sub(USER_MENTION_PATTERN, urlize_user, text)
    text = re.sub(TICKET_MENTION_PATTERN, urlize_ticket, text)

    return markdown(text)


def label_badge(label, cls="", remove_from_ticket=None):
    """Return HTML markup rendering a label badge.

    Additional HTML classes can be passed via the `cls` parameter.

    If a Ticket is passed in `remove_from_ticket`, a removal button will also
    be rendered for removing the label from given ticket.
    """
    name = escape(label.name)
    color = escape(label.text_color)
    bg_color = escape(label.color)
    html_class = escape(f"label {cls}".strip())

    style = f"color: {color}; background-color: {bg_color}"
    search_url = urls.label_search_url(label)

    if remove_from_ticket:
        remove_url = urls.label_remove_url(label, remove_from_ticket)
        remove_form = f"""
            <form method="POST" action="{remove_url}">
              {csrf_token()}
              <button type="submit" class="btn btn-link">
                {icon('times')}
              </button>
            </form>
        """
    else:
        remove_form = ""

    return Markup(
        f"""<span style="{style}" class="{html_class}" href="{search_url}">
            <a href="{search_url}">{name}</a>
            {remove_form}
        </span>"""
    )
