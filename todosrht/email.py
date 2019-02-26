import html.parser
import os
import pystache
import textwrap
from flask_login import current_user
from srht.config import cfg, cfgi
from srht.email import send_email, lookup_key

origin = cfg("todo.sr.ht", "origin")

def format_lines(text, quote=False):
    wrapped = textwrap.wrap(text, width=72,
            replace_whitespace=False, expand_tabs=False, drop_whitespace=False)
    return "\n".join(wrapped)

def notify(sub, template, subject, headers, **kwargs):
    encrypt_key = None
    if sub.email:
        to = sub.email
    elif sub.user:
        to = sub.user.email
        encrypt_key = lookup_key(sub.user.username, sub.user.oauth_token)
    else:
        return # TODO
    with open(os.path.join(os.path.dirname(__file__), "emails", template)) as f:
        body = html.unescape(
            pystache.render(f.read(), {
                'user': current_user,
                'root': origin,
                'format_lines': format_lines,
                **kwargs
            }))
    send_email(body, to, subject, encrypt_key=encrypt_key, **headers)
