from srht.database import db
from todosrht.tickets import assign, unassign

from .factories import UserFactory, TicketFactory


def test_assignment():
    ticket = TicketFactory()
    assigner = UserFactory()

    assignee1 = UserFactory()
    assignee2 = UserFactory()
    db.session.commit()

    assert ticket.assigned_users == []

    assign(ticket, assignee1, assigner)
    db.session.commit()
    assert set(ticket.assigned_users) == {assignee1}

    # Assignment is idempotent
    assign(ticket, assignee1, assigner)
    db.session.commit()
    assert set(ticket.assigned_users) == {assignee1}

    assign(ticket, assignee2, assigner)
    db.session.commit()
    assert set(ticket.assigned_users) == {assignee1, assignee2}

    unassign(ticket, assignee1, assigner)
    db.session.commit()
    assert set(ticket.assigned_users) == {assignee2}

    # Unassignment is also idempotent
    unassign(ticket, assignee1, assigner)
    db.session.commit()
    assert set(ticket.assigned_users) == {assignee2}

    unassign(ticket, assignee2, assigner)
    db.session.commit()
    assert ticket.assigned_users == []
