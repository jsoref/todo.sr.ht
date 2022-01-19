import re
from collections import namedtuple
from datetime import datetime
from itertools import chain
from srht.config import cfg
from srht.database import db
from todosrht.email import notify, format_lines
from todosrht.types import Event, EventType, EventNotification
from todosrht.types import TicketComment, TicketStatus, TicketSubscription
from todosrht.types import TicketAssignee, User, Ticket, Tracker
from todosrht.types import Participant, ParticipantType
from todosrht.urls import ticket_url
from sqlalchemy import func, or_, and_

smtp_user = cfg("mail", "smtp-user", default=None)
smtp_from = cfg("mail", "smtp-from", default=None)
notify_from = cfg("todo.sr.ht", "notify-from", default=smtp_from)
posting_domain = cfg("todo.sr.ht::mail", "posting-domain")
origin = cfg("todo.sr.ht", "origin")

StatusChange = namedtuple("StatusChange", [
    "old_status",
    "new_status",
    "old_resolution",
    "new_resolution",
])

# Matches user mentions, e.g. ~username
USER_MENTION_PATTERN = re.compile(r"""
    (?<![^\s(])  # No leading non-whitespace characters
    ~            # Literal tilde
    (\w+)        # The username
    \b           # Word boundary
    (?!/)        # Not followed by slash, possible qualified ticket mention
""", re.VERBOSE)

# Matches ticket mentions, e.g. #17, tracker#17 and ~user/tracker#17
TICKET_MENTION_PATTERN = re.compile(r"""
    (?<![^\s(])                         # No leading non-whitespace characters
    (~(?P<username>\w+)/)?              # Optional username
    (?P<tracker_name>[A-Za-z0-9_.-]+)?  # Optional tracker name
    \#(?P<ticket_id>\d+)                # Ticket ID
    \b                                  # Word boundary
""", re.VERBOSE)

# Matches ticket URL
TICKET_URL_PATTERN = re.compile(f"""
    (?<![^\\s(])                        # No leading non-whitespace characters
    {origin}/                           # Base URL
    ~(?P<username>\\w+)/                # Username
    (?P<tracker_name>[A-Za-z0-9_.-]+)/  # Tracker name
    (?P<ticket_id>\\d+)                 # Ticket ID
    \\b                                 # Word boundary
""", re.VERBOSE)

def get_participant_for_user(user):
    participant = Participant.query.filter(
            Participant.user_id == user.id).one_or_none()
    if not participant:
        participant = Participant()
        participant.user_id = user.id
        participant.participant_type = ParticipantType.user
        db.session.add(participant)
        db.session.flush()
    return participant

def get_participant_for_email(email, email_name=None):
    user = User.query.filter(User.email == email).one_or_none()
    if user:
        return get_participant_for_user(user)
    participant = Participant.query.filter(
            Participant.email == email).one_or_none()
    if not participant:
        participant = Participant()
        participant.email = email
        participant.email_name = email_name
        participant.participant_type = ParticipantType.email
        db.session.add(participant)
        db.session.flush()
    return participant

def get_participant_for_external(external_id, external_url):
    participant = Participant.query.filter(
            Participant.external_id == external_id).one_or_none()
    if not participant:
        participant = Participant()
        participant.external_id = external_id
        participant.external_url = external_url
        participant.participant_type = ParticipantType.external
        db.session.add(participant)
        db.session.flush()
    return participant

def find_mentioned_users(text):
    if text is None:
        return set()
    # TODO: Find mentioned email addresses as well
    usernames = re.findall(USER_MENTION_PATTERN, text)
    users = User.query.filter(User.username.in_(usernames)).all()
    participants = set([get_participant_for_user(u) for u in set(users)])
    return participants

def find_mentioned_tickets(tracker, text):
    if text is None:
        return set()
    filters = []
    matches = chain(
        re.finditer(TICKET_MENTION_PATTERN, text),
        re.finditer(TICKET_URL_PATTERN, text),
    )

    for match in matches:
        username = match.group('username') or tracker.owner.username
        tracker_name = match.group('tracker_name') or tracker.name
        ticket_id = int(match.group('ticket_id'))

        filters.append(and_(
            Ticket.scoped_id == ticket_id,
            Tracker.name == tracker_name,
            User.username == username,
        ))

    # No tickets mentioned
    if len(filters) == 0:
        return set()

    return set(Ticket.query
        .join(Tracker, User)
        .filter(or_(*filters))
        .all())

def _create_comment(ticket, participant, text):
    comment = TicketComment()
    comment.text = text
    comment.submitter_id = participant.id
    comment.ticket_id = ticket.id

    db.session.add(comment)
    db.session.flush()
    return comment

def _create_comment_event(ticket, participant, comment, status_change):
    event = Event()
    event.event_type = 0
    event.participant_id = participant.id
    event.ticket_id = ticket.id

    if comment:
        event.event_type |= EventType.comment
        event.comment_id = comment.id

    if status_change:
        event.event_type |= EventType.status_change
        event.old_status = status_change.old_status
        event.old_resolution = status_change.old_resolution
        event.new_status = status_change.new_status
        event.new_resolution = status_change.new_resolution

    db.session.add(event)
    db.session.flush()
    return event

def _create_event_notification(participant, event):
    if participant.participant_type != ParticipantType.user:
        return None # We only record notifications for registered users
    notification = EventNotification()
    notification.user_id = participant.user.id
    notification.event_id = event.id
    db.session.add(notification)
    return notification

def _send_comment_notification(subscription, ticket,
        participant, event, comment, resolution):
    subject = "Re: {}: {}".format(ticket.ref(), ticket.title)
    subscription_ref = subscription.tracker.ref() if subscription.tracker \
            else ticket.ref(email=True)
    headers = {
        "From": "{} <{}>".format(participant.name, notify_from),
        "In-Reply-To": f"<{ticket.ref(email=True)}@{posting_domain}>",
        "Reply-To": f"{ticket.ref()} <{ticket.ref(email=True)}@{posting_domain}>",
        "Sender": f"<{smtp_user}@{posting_domain}>",
        "List-Unsubscribe": f"mailto:{subscription_ref}/unsubscribe" +
            f"@{posting_domain}"
    }

    url = ticket_url(ticket, event=event)

    notify(subscription, "ticket_comment", subject,
        headers=headers,
        ticket=ticket,
        comment=comment,
        comment_text=format_lines(comment.text) if comment else "",
        resolution=f"""Ticket resolved: {resolution.name}\n\n""" if resolution else "",
        ticket_url=url)

def _change_ticket_status(ticket, resolve, resolution, reopen):
    if not (resolve or reopen):
        return None

    old_status = ticket.status
    old_resolution = ticket.resolution

    if resolve:
        if old_status == TicketStatus.resolved and old_resolution == resolution:
            return None
        ticket.status = TicketStatus.resolved
        ticket.resolution = resolution

    if reopen:
        if old_status == TicketStatus.reported:
            return None
        ticket.status = TicketStatus.reported

    return StatusChange(old_status, ticket.status,
            old_resolution, ticket.resolution)

def _send_comment_notifications(
        participant, ticket, event, comment, resolution, from_email):
    """
    Notify users subscribed to the ticket or tracker.
    Returns a list of notified users.
    """
    # Find subscribers, eliminate duplicates
    subscriptions = {sub.participant: sub
        for sub in ticket.tracker.subscriptions + ticket.subscriptions}

    # Subscribe commenter if not already subscribed
    if participant not in subscriptions:
        subscription = TicketSubscription()
        subscription.ticket_id = ticket.id
        subscription.participant = participant
        subscription.participant_id = participant.id
        db.session.add(subscription)
        subscriptions[participant] = subscription

    for subscriber, subscription in subscriptions.items():
        _create_event_notification(subscriber, event)
        if (participant.notify_self and not from_email) or subscriber != participant:
            _send_comment_notification(
                subscription, ticket, participant, event, comment, resolution)

    return subscriptions.keys()

def _send_mention_notification(sub, submitter, text, ticket, comment=None):
    subject = "{}: {}".format(ticket.ref(), ticket.title)
    subscription_ref = sub.tracker.ref() if sub.tracker \
            else ticket.ref(email=True)
    headers = {
        "From": "{} <{}>".format(submitter.name, notify_from),
        "In-Reply-To": f"<{ticket.ref(email=True)}@{posting_domain}>",
        "Reply-To": f"{ticket.ref()} <{ticket.ref(email=True)}@{posting_domain}>",
        "Sender": f"<{smtp_user}@{posting_domain}>",
        "List-Unsubscribe": f"mailto:{subscription_ref}/unsubscribe" +
            f"@{posting_domain}"
    }

    context = {
        "text": format_lines(text),
        "submitter": submitter.name,
        "ticket_ref": ticket.ref(),
        "ticket_url": ticket_url(ticket, comment),
    }

    notify(sub, "ticket_mention", subject, headers, **context)


def _handle_mentions(ticket, submitter, text, notified_users, comment=None):
    """
    Create events for mentioned tickets and users and notify mentioned users.
    """
    mentioned_participants = find_mentioned_users(text)
    mentioned_tickets = find_mentioned_tickets(ticket.tracker, text)

    for participant in mentioned_participants:
        db.session.add(Event(
            event_type=EventType.user_mentioned,
            participant=participant,
            from_ticket=ticket,
            by_participant=submitter,
            comment=comment,
        ))

    for mentioned_ticket in mentioned_tickets:
        if mentioned_ticket != ticket:
            db.session.add(Event(
                event_type=EventType.ticket_mentioned,
                ticket=mentioned_ticket,
                from_ticket=ticket,
                by_participant=submitter,
                comment=comment,
            ))

    # Notify users who are mentioned, but only if they haven't already received
    # a notification due to being subscribed to the event or tracker
    # Also don't notify the submitter if they mention themselves.
    to_notify = mentioned_participants - set(notified_users) - set([submitter])
    for target in to_notify:
        sub = get_or_create_subscription(ticket, target)
        _send_mention_notification(sub, submitter, text, ticket, comment)


def add_comment(submitter, ticket,
        text=None, resolve=False, resolution=None, reopen=False,
        from_email=False):
    """
    Comment on a ticket, optionally resolve or reopen the ticket.
    """
    # TODO better error handling
    assert text or resolve or reopen
    assert not (resolve and reopen)
    if resolve:
        assert resolution is not None

    comment = _create_comment(ticket, submitter, text) if text else None
    status_change = _change_ticket_status(ticket, resolve, resolution, reopen)
    if not comment and not status_change:
        return None
    event = _create_comment_event(ticket, submitter, comment, status_change)
    notified_participants = _send_comment_notifications(
        submitter, ticket, event, comment, resolution, from_email)

    if comment and comment.text:
        _handle_mentions(
            ticket,
            comment.submitter,
            comment.text,
            notified_participants,
            comment,
        )

    ticket.comment_count = get_comment_count(ticket.id)
    ticket.updated = datetime.utcnow()
    ticket.tracker.updated = datetime.utcnow()
    db.session.commit()

    return event

def get_or_create_subscription(ticket, participant):
    """
    If participant is subscribed to ticket or tracker, returns that
    subscription, otherwise subscribes the user to the ticket and returns that
    one.
    """
    subscription = TicketSubscription.query.filter(
        (TicketSubscription.participant == participant) & (
            (TicketSubscription.ticket == ticket) |
            (TicketSubscription.tracker == ticket.tracker)
        )
    ).first()

    if not subscription:
        subscription = TicketSubscription(
                ticket=ticket, participant=participant)
        db.session.add(subscription)

    return subscription

# TODO: support arbitrary participants being assigned to tickets
def notify_assignee(subscription, ticket, assigner, assignee):
    """
    Sends a notification email to the person who was assigned to the issue.
    """
    subject = "{}: {}".format(ticket.ref(), ticket.title)
    subscription_ref = subscription.tracker.ref() if subscription.tracker \
            else ticket.ref(email=True)
    headers = {
        "From": "~{} <{}>".format(assigner.username, notify_from),
        "In-Reply-To": f"<{ticket.ref(email=True)}@{posting_domain}>",
        "Reply-To": f"{ticket.ref()} <{ticket.ref(email=True)}@{posting_domain}>",
        "Sender": f"<{smtp_user}@{posting_domain}>",
        "List-Unsubscribe": f"mailto:{subscription_ref}/unsubscribe" +
            f"@{posting_domain}"
    }

    context = {
        "assigner": assigner.canonical_name,
        "ticket_ref": ticket.ref(),
        "ticket_url": ticket_url(ticket)
    }

    notify(subscription, "ticket_assigned", subject, headers, **context)

def assign(ticket, assignee, assigner):
    ticket_assignee = TicketAssignee.query.filter_by(
        ticket=ticket, assignee=assignee).one_or_none()

    # If already assigned, do nothing
    if ticket_assignee:
        return ticket_assignee

    ticket_assignee = TicketAssignee(
        ticket=ticket,
        assignee=assignee,
        assigner=assigner,
    )
    db.session.add(ticket_assignee)

    assignee_participant = get_participant_for_user(assignee)
    assigner_participant = get_participant_for_user(assigner)

    subscription = get_or_create_subscription(ticket, assignee_participant)
    if assigner.notify_self or assigner != assignee:
        notify_assignee(subscription, ticket, assigner, assignee)

    event = Event()
    event.event_type = EventType.assigned_user
    event.participant_id = assignee_participant.id
    event.ticket_id = ticket.id
    event.by_participant_id = assigner_participant.id
    db.session.add(event)

    return ticket_assignee

def unassign(ticket, assignee, assigner):
    ticket_assignee = TicketAssignee.query.filter_by(
        ticket=ticket, assignee=assignee).one_or_none()

    # If not assigned, do nothing
    if not ticket_assignee:
        return None

    db.session.delete(ticket_assignee)

    assignee_participant = get_participant_for_user(assignee)
    assigner_participant = get_participant_for_user(assigner)

    event = Event()
    event.event_type = EventType.unassigned_user
    event.participant_id = assignee_participant.id
    event.ticket_id = ticket.id
    event.by_participant_id = assigner_participant.id
    db.session.add(event)

def get_comment_count(ticket_id):
    """Returns the number of comments on a given ticket."""
    return (
        TicketComment.query
        .filter_by(ticket_id=ticket_id, superceeded_by_id=None)
        .count()
    )

def _send_new_ticket_notification(subscription, ticket, email_trigger_id):
    subject = f"{ticket.ref()}: {ticket.title}"
    subscription_ref = subscription.tracker.ref() if subscription.tracker \
            else ticket.ref(email=True)
    headers = {
        "From": "{} <{}>".format(ticket.submitter.name, notify_from),
        "Message-ID": f"<{ticket.ref(email=True)}@{posting_domain}>",
        "Reply-To": f"{ticket.ref()} <{ticket.ref(email=True)}@{posting_domain}>",
        "Sender": f"<{smtp_user}@{posting_domain}>",
        "List-Unsubscribe": f"mailto:{subscription_ref}/unsubscribe" +
            f"@{posting_domain}"
    }
    if email_trigger_id:
        headers["In-Reply-To"] = email_trigger_id

    notify(subscription, "new_ticket", subject,
        headers=headers, description=ticket.description,
        ticket_url=ticket_url(ticket))

def submit_ticket(tracker, submitter, title, description,
        importing=False, from_email=False, from_email_id=None):
    ticket = Ticket(
        submitter=submitter,
        tracker=tracker,
        scoped_id=tracker.next_ticket_id,
        title=title,
        description=description,
    )
    db.session.add(ticket)
    db.session.flush()

    tracker.next_ticket_id += 1
    tracker.updated = datetime.utcnow()

    event = Event(event_type=EventType.created,
            participant=submitter, ticket=ticket)
    db.session.add(event)
    db.session.flush()

    # Subscribe submitter to the ticket if not already subscribed to the tracker
    if not importing:
        get_or_create_subscription(ticket, submitter)
        all_subscriptions = {sub.participant: sub
                for sub
                in ticket.subscriptions + tracker.subscriptions}

        # Send notifications
        for sub in all_subscriptions.values():
            _create_event_notification(sub.participant, event)
            # Always notify submitter for tickets created by email
            if from_email or submitter.notify_self or sub.participant != submitter:
                _send_new_ticket_notification(sub, ticket, from_email_id)

        _handle_mentions(
            ticket,
            ticket.submitter,
            ticket.description,
            all_subscriptions.keys(),
        )

        db.session.commit()
    return ticket
