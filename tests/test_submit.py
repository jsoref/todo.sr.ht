import pytest
from itertools import chain
from srht.database import db
from tests.factories import UserFactory, TrackerFactory, TicketFactory
from tests.factories import ParticipantFactory
from todosrht.tickets import submit_ticket
from todosrht.types import Ticket, EventType, TicketSubscription, Event
from todosrht.urls import ticket_url

@pytest.mark.parametrize("submitter_subscribed", [True, False])
def test_submit_ticket(client, mailbox, submitter_subscribed):
    tracker = TrackerFactory()
    submitter = ParticipantFactory()

    subscriber = ParticipantFactory()
    TicketSubscription(participant=subscriber, tracker=tracker)

    # `submitter_subscribed` parameter defines whether the submitter was
    # subscribed to the tracker prior to submitting the ticket
    # this affects whether a new subscription is created when submitting
    if submitter_subscribed:
        TicketSubscription(participant=submitter, tracker=tracker)

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
    assert event.participant == submitter

    # Check subscriber got an email
    assert len(mailbox) == 1
    email = mailbox[0]
    assert email.to == subscriber.user.email
    assert title in email.subject
    assert ticket.ref() in email.subject
    assert description in email.body
    assert ticket_url(ticket) in email.body
    assert email.headers['From'].startswith(submitter.name)

    # Check event notification is created for the subscriber
    assert len(subscriber.user.notifications) == 1
    notification = subscriber.user.notifications[0]
    assert notification.event == event

    # Check submitter is subscribed to the ticket
    if submitter_subscribed:
        next((s for s in submitter.subscriptions if s.tracker == tracker))
    else:
        next((s for s in submitter.subscriptions if s.ticket == ticket))


def test_mentions_in_ticket_description(mailbox):
    owner = UserFactory()
    tracker = TrackerFactory(owner=owner)
    submitter = ParticipantFactory()

    t1 = TicketFactory(tracker=tracker)
    t2 = TicketFactory(tracker=tracker)
    t3 = TicketFactory(tracker=tracker)

    p1 = ParticipantFactory()
    p2 = ParticipantFactory()

    subscriber = ParticipantFactory()
    TicketSubscription(participant=subscriber, tracker=tracker)

    db.session.flush()
    tracker.next_ticket_id = t3.id + 1
    db.session.commit()

    title = "foo"
    description = f"""
    Testing mentioning
    ---------------
    myself: {submitter.identifier}
    user one: {p1.identifier}
    user two: {p2.identifier}
    nonexistant user: ~hopefullythisuserdoesnotexist
    subscriber: {subscriber.identifier}
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
        assert event.participant is None
        assert event.comment is None
        assert event.from_ticket == ticket
        assert event.by_participant == submitter

    # Check user events, skip the ticket create event
    submitter_events = [e for e in submitter.events
        if e.event_type != EventType.created]

    assert len(submitter_events) == 1
    assert len(p1.events) == 1
    assert len(p2.events) == 1
    assert len(subscriber.events) == 1

    for event in chain(
        submitter_events, p1.events, p2.events, subscriber.events
    ):
        assert event.event_type == EventType.user_mentioned
        assert event.ticket is None
        assert event.comment is None
        assert event.from_ticket == ticket
        assert event.by_participant == submitter

    # Check emails
    # Submitter should not have been emailed since they mentioned themselves
    assert len(mailbox) == 3

    subscriber_email = next(e for e in mailbox if e.to == subscriber.user.email)
    p1_email = next(e for e in mailbox if e.to == p1.user.email)
    p2_email = next(e for e in mailbox if e.to == p2.user.email)

    # Subscriber should receive a notification that the ticket was created so
    # they're not sent a notification for the mention.
    assert subscriber_email.body.strip().startswith("Testing mentioning")

    # Other mentioned users who are not subscribed should get a mention email
    expected = f"You were mentioned in {ticket.ref()} by {submitter.name}."
    assert p1_email.body.startswith(expected)
    assert p2_email.body.startswith(expected)
