from srht.database import db
from todosrht.tickets import assign, unassign

from .factories import UserFactory, TrackerFactory, TicketFactory


def test_assignment(mailbox):
    owner = UserFactory(username="foo")
    tracker = TrackerFactory(owner=owner, name="bar")
    ticket = TicketFactory(tracker=tracker, scoped_id=1, title="Hilfe!")
    assigner = UserFactory(username="assigner")

    assignee1 = UserFactory()
    assignee2 = UserFactory()
    db.session.commit()

    assert ticket.assigned_users == []

    assign(ticket, assignee1, assigner)
    db.session.commit()
    assert set(ticket.assigned_users) == {assignee1}

    assert len(mailbox) == 1
    assert mailbox[0].to == assignee1.email
    assert mailbox[0].subject == "~foo/bar#1: Hilfe!"
    assert mailbox[0].body.startswith(
        "You were assigned to ~foo/bar#1 by ~assigner")
    assert mailbox[0].headers["In-Reply-To"] == (
        f'<~{tracker.owner.username}/{tracker.name}/{ticket.scoped_id}@example.org>'
    )

    # Assignment is idempotent
    assign(ticket, assignee1, assigner)
    db.session.commit()
    assert set(ticket.assigned_users) == {assignee1}

    assign(ticket, assignee2, assigner)
    db.session.commit()
    assert set(ticket.assigned_users) == {assignee1, assignee2}

    assert len(mailbox) == 2
    assert mailbox[1].to == assignee2.email
    assert mailbox[1].subject == "~foo/bar#1: Hilfe!"
    assert mailbox[1].body.startswith(
        "You were assigned to ~foo/bar#1 by ~assigner")
    assert mailbox[1].headers["In-Reply-To"] == (
        f'<~{tracker.owner.username}/{tracker.name}/{ticket.scoped_id}@example.org>'
    )

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

    # No more emails were sent
    assert len(mailbox) == 2

def test_email_not_sent_when_self_assigned(mailbox):
    ticket = TicketFactory()
    user = UserFactory()
    db.session.commit()

    assign(ticket, user, user)
    db.session.commit()

    assert set(ticket.assigned_users) == {user}
    assert len(mailbox) == 0
