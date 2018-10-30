import os
from srht.email import send_email, lookup_key
import html.parser
import pystache
from srht.config import cfg, cfgi
from flask_login import current_user

origin = cfg("todo.sr.ht", "origin")

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
                **kwargs
            }))
    send_email(body, to, subject, encrypt_key=encrypt_key, **headers)
