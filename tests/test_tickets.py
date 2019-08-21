from srht.database import db
from tests.factories import TrackerFactory, TicketFactory, UserFactory
from tests.factories import ParticipantFactory
from tests.utils import logged_in_as
from todosrht.tickets import get_or_create_subscription
from todosrht.types import TicketSeen, TicketSubscription
from todosrht.urls import ticket_url

def test_mark_seen(client):
    ticket = TicketFactory()
    user = UserFactory()
    db.session.commit()

    url = ticket_url(ticket)

    query = TicketSeen.query.filter_by(user=user, ticket=ticket)
    assert query.count() == 0

    # Created on first visit
    with logged_in_as(user):
        response = client.get(url)
        assert response.status_code == 200

    first_time = query.one().last_view

    # Updated on second visit
    with logged_in_as(user):
        response = client.get(url)
        assert response.status_code == 200

    second_time = query.one().last_view

    assert second_time > first_time

def test_get_or_create_subscription():
    participant1 = ParticipantFactory()
    participant2 = ParticipantFactory()
    participant3 = ParticipantFactory()
    tracker = TrackerFactory()
    ticket = TicketFactory(tracker=tracker)

    # Some existing subscriptions
    ts1 = TicketSubscription(participant=participant1, ticket=ticket)
    ts2 = TicketSubscription(participant=participant2, tracker=tracker)
    db.session.add(ts1)
    db.session.add(ts2)
    db.session.commit()

    assert set(ticket.subscriptions) == set([ts1])
    assert set(tracker.subscriptions) == set([ts2])

    # Return existing subs if they exist
    assert get_or_create_subscription(ticket, participant1) == ts1
    assert get_or_create_subscription(ticket, participant2) == ts2

    # Create new ticket sub if none exists
    ts3 = get_or_create_subscription(ticket, participant3)
    db.session.commit()

    assert set(ticket.subscriptions) == set([ts1, ts3])
    assert set(tracker.subscriptions) == set([ts2])
