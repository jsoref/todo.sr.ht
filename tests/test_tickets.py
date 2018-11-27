from srht.database import db
from tests.factories import TicketFactory, UserFactory
from tests.utils import logged_in_as
from todosrht.types import TicketSeen
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
