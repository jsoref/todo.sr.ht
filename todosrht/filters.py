from jinja2.utils import Markup, escape
from srht.flask import icon, csrf_token
from todosrht import urls


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
