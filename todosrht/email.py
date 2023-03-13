import os
import textwrap
from string import Template
from srht.config import cfg
from srht.crypto import internal_anon
from srht.graphql import exec_gql
from todosrht.types import ParticipantType

origin = cfg("todo.sr.ht", "origin")

def format_lines(text, quote=False):
    wrapped = textwrap.wrap(text, width=72,
            replace_whitespace=False, expand_tabs=False, drop_whitespace=False)
    return "\n".join(wrapped)

def notify(sub, template, subject, headers, **kwargs):
    to = sub.participant
    if to.participant_type == ParticipantType.external:
        return
    with open(os.path.join(os.path.dirname(__file__), "emails", template)) as f:
        tmpl = Template(f.read())
        body = tmpl.substitute(**{
            'root': origin,
            **kwargs,
        })
    if to.participant_type == ParticipantType.email:
        address = f"{to.email}"
    elif to.participant_type == ParticipantType.user:
        address = to.user.email

    msg = f"Subject: {subject}\n"
    for hdr, val in headers.items():
        msg += f"{hdr}: {val}\n"
    msg += "\n" + body
    email_mutation = """
    mutation SendEmail($address: String!, $msg: String!) {
        sendEmail(address: $address, message: $msg)
    }
    """
    r = exec_gql("meta.sr.ht", email_mutation, user=internal_anon,
        address=address, msg=msg)
