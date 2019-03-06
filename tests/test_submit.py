import pytest
from srht.database import db
from tests.factories import UserFactory, TrackerFactory
from todosrht.tickets import submit_ticket
from todosrht.urls import ticket_url
from todosrht.types import Ticket, EventType, TicketSubscription

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
