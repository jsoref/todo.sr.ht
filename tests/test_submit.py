import pytest
from itertools import chain
from srht.database import db
from tests.factories import UserFactory, TrackerFactory, TicketFactory
from todosrht.tickets import submit_ticket
from todosrht.types import Ticket, EventType, TicketSubscription, Event
from todosrht.urls import ticket_url

@pytest.mark.parametrize("submitter_subscribed", [True, False])
def test_submit_ticket(client, mailbox, submitter_subscribed):
    tracker = TrackerFactory()
    submitter = UserFactory()

    subscriber = UserFactory()
    TicketSubscription(user=subscriber, tracker=tracker)

    # `submitter_subscribed` parameter defines whether the submitter was
    # subscribed to the tracker prior to submitting the ticket
    # this affects whether a new subscription is created when submitting
    if submitter_subscribed:
        TicketSubscription(user=submitter, tracker=tracker)

    db.session.commit()

    title = "I have a problem"
    description = "It does not work."

    ticket = submit_ticket(tracker, submitter, title, description)

    # Check ticket is created
    assert isinstance(ticket, Ticket)
    assert ticket.tracker == tracker
    assert ticket.submitter == submitter
    assert ticket.description == description
    assert ticket.scoped_id == 1
    assert tracker.next_ticket_id == 2

    # Check event is created
    assert len(ticket.events) == 1
    event = ticket.events[0]
    assert event.event_type == EventType.created
    assert event.ticket == ticket
    assert event.user == submitter

    # Check subscriber got an email
    assert len(mailbox) == 1
    email = mailbox[0]
    assert email.to == subscriber.email
    assert title in email.subject
    assert ticket.ref() in email.subject
    assert description in email.body
    assert ticket_url(ticket) in email.body
    assert email.headers['From'].startswith(submitter.canonical_name)

    # Check event notification is created for the subscriber
    assert len(subscriber.notifications) == 1
    notification = subscriber.notifications[0]
    assert notification.event == event

    # Check submitter is subscribed to the ticket
    assert len(submitter.subscriptions) == 1
    subscription = submitter.subscriptions[0]
    if submitter_subscribed:
        assert subscription.tracker == tracker
        assert subscription.ticket is None
    else:
        assert subscription.tracker is None
        assert subscription.ticket == ticket


def test_mentions_in_ticket_description(mailbox):
    owner = UserFactory()
    tracker = TrackerFactory(owner=owner)
    submitter = UserFactory()

    t1 = TicketFactory(tracker=tracker)
    t2 = TicketFactory(tracker=tracker)
    t3 = TicketFactory(tracker=tracker)

    u1 = UserFactory()
    u2 = UserFactory()

    subscriber = UserFactory()
    TicketSubscription(user=subscriber, tracker=tracker)

    db.session.flush()
    tracker.next_ticket_id = t3.id + 1
    db.session.commit()

    title = "foo"
    description = f"""
    Testing mentioning
    ---------------
    myself: {submitter.canonical_name}
    user one: {u1.canonical_name}
    user two: {u2.canonical_name}
    nonexistant user: ~hopefullythisuserdoesnotexist
    subscriber: {subscriber.canonical_name}
    ticket one: #{t1.scoped_id}
    ticket two: {tracker.name}#{t2.scoped_id}
    ticket three: {owner.canonical_name}/{tracker.name}#{t3.scoped_id}
    """

    ticket = submit_ticket(tracker, submitter, title, description)

    # Four user mentions and three ticket mentions total
    assert Event.query.filter_by(from_ticket=ticket).count() == 7

    # Check ticket events
    assert len(t1.events) == 1
    assert len(t2.events) == 1
    assert len(t3.events) == 1

    for event in chain(t1.events, t2.events, t3.events):
        assert event.event_type == EventType.ticket_mentioned
        assert event.user is None
        assert event.comment is None
        assert event.from_ticket == ticket
        assert event.by_user == submitter

    # Check user events, skip the ticket create event
    submitter_events = [e for e in submitter.events
        if e.event_type != EventType.created]

    assert len(submitter_events) == 1
    assert len(u1.events) == 1
    assert len(u2.events) == 1
    assert len(subscriber.events) == 1

    for event in chain(
        submitter_events, u1.events, u2.events, subscriber.events
    ):
        assert event.event_type == EventType.user_mentioned
        assert event.ticket is None
        assert event.comment is None
        assert event.from_ticket == ticket
        assert event.by_user == submitter

    # Check emails
    # Submitter should not have been emailed since they mentioned themselves
    assert len(mailbox) == 3

    subscriber_email = next(e for e in mailbox if e.to == subscriber.email)
    u1_email = next(e for e in mailbox if e.to == u1.email)
    u2_email = next(e for e in mailbox if e.to == u2.email)

    # Subscriber should receive a notification that the ticket was created so
    # they're not sent a notification for the mention.
    assert subscriber_email.body.strip().startswith("Testing mentioning")

    # Other mentioned users who are not subscribed should get a mention email
    expected = f"You were mentioned in {ticket.ref()} by {submitter}."
    assert u1_email.body.startswith(expected)
    assert u2_email.body.startswith(expected)
