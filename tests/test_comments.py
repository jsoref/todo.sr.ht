import pytest
from srht.database import db
from todosrht.tickets import add_comment, find_mentioned_users
from todosrht.types import TicketResolution, TicketStatus
from todosrht.types import TicketSubscription, EventType

from .factories import UserFactory, TrackerFactory, TicketFactory

def test_ticket_comment(mailbox):
    user = UserFactory()
    tracker = TrackerFactory()
    ticket = TicketFactory(tracker=tracker)

    subscribed_to_ticket = UserFactory()
    subscribed_to_tracker = UserFactory()
    subscribed_to_both = UserFactory()

    sub1 = TicketSubscription(user=subscribed_to_ticket, ticket=ticket)
    sub2 = TicketSubscription(user=subscribed_to_tracker, tracker=tracker)
    sub3 = TicketSubscription(user=subscribed_to_both, ticket=ticket)
    sub4 = TicketSubscription(user=subscribed_to_both, tracker=tracker)

    db.session.add(sub1)
    db.session.add(sub2)
    db.session.add(sub3)
    db.session.add(sub4)
    db.session.flush()

    def assert_notifications_sent(starts_with=""):
        """Checks a notification was sent to the three subscribed users."""
        emails = mailbox[-3:]

        assert {e.to for e in emails} == {
            subscribed_to_ticket.email,
            subscribed_to_tracker.email,
            subscribed_to_both.email,
        }

        for e in emails:
            assert e.headers['From'].startswith(user.canonical_name)
            if starts_with:
                assert e.body.startswith(starts_with)

    def assert_event_notifications_created(event):
        assert {en.user.email for en in event.notifications} == {
            subscribed_to_ticket.email,
            subscribed_to_tracker.email,
            subscribed_to_both.email,
            event.user.email,
        }

    assert len(mailbox) == 0
    assert ticket.status == TicketStatus.reported
    assert ticket.resolution == TicketResolution.unresolved

    # Comment without status change
    comment = add_comment(user, ticket, text="how do you do, i")

    # Submitter gets automatically subscribed
    assert TicketSubscription.query.filter_by(ticket=ticket, user=user).first()

    assert comment.submitter == user
    assert comment.ticket == ticket
    assert comment.text == "how do you do, i"

    assert ticket.status == TicketStatus.reported
    assert ticket.resolution == TicketResolution.unresolved
    assert len(ticket.comments) == 1
    assert len(ticket.events) == 1

    event = ticket.events[0]
    assert event.ticket == ticket
    assert event.comment == comment
    assert event.event_type == EventType.comment

    assert len(mailbox) == 3
    assert_notifications_sent(comment.text)
    assert_event_notifications_created(event)

    # Comment and resolve issue
    comment = add_comment(user, ticket, text="see you've met my",
            resolve=True, resolution=TicketResolution.fixed)

    assert comment.submitter == user
    assert comment.ticket == ticket
    assert comment.text == "see you've met my"

    assert ticket.status == TicketStatus.resolved
    assert ticket.resolution == TicketResolution.fixed
    assert len(ticket.comments) == 2
    assert len(ticket.events) == 2

    event = ticket.events[1]
    assert event.ticket == ticket
    assert event.comment == comment
    assert event.event_type == EventType.status_change | EventType.comment
    assert event.old_status == TicketStatus.reported
    assert event.new_status == TicketStatus.resolved
    assert event.old_resolution == TicketResolution.unresolved
    assert event.new_resolution == TicketResolution.fixed

    assert len(mailbox) == 6
    assert_notifications_sent("Ticket resolved: fixed")
    assert_event_notifications_created(event)

    # Comment and reopen issue
    comment = add_comment(user, ticket, text="faithful handyman", reopen=True)

    assert comment.submitter == user
    assert comment.ticket == ticket
    assert comment.text == "faithful handyman"

    assert ticket.status == TicketStatus.reported
    assert ticket.resolution == TicketResolution.fixed
    assert len(ticket.comments) == 3
    assert len(ticket.events) == 3

    event = ticket.events[2]
    assert event.ticket == ticket
    assert event.comment == comment

    assert len(mailbox) == 9
    assert_notifications_sent(comment.text)
    assert_event_notifications_created(event)

    # Resolve without commenting
    comment = add_comment(user, ticket,
            resolve=True, resolution=TicketResolution.wont_fix)

    assert comment is None

    assert ticket.status == TicketStatus.resolved
    assert ticket.resolution == TicketResolution.wont_fix
    assert len(ticket.comments) == 3
    assert len(ticket.events) == 4

    event = ticket.events[3]
    assert event.ticket == ticket
    assert event.comment == comment

    assert len(mailbox) == 12
    assert_notifications_sent("Ticket resolved: wont_fix")
    assert_event_notifications_created(event)

    # Reopen without commenting
    comment = add_comment(user, ticket, reopen=True)

    assert comment is None

    assert ticket.status == TicketStatus.reported
    assert ticket.resolution == TicketResolution.wont_fix
    assert len(ticket.comments) == 3
    assert len(ticket.events) == 5

    event = ticket.events[4]
    assert event.ticket == ticket
    assert event.comment == comment

    assert len(mailbox) == 15
    assert_notifications_sent()
    assert_event_notifications_created(event)


def test_failed_comments():
    user = UserFactory()
    tracker = TrackerFactory()
    ticket = TicketFactory(tracker=tracker)
    db.session.flush()

    with pytest.raises(AssertionError):
        add_comment(user, ticket)


def test_find_mentioned_users():
    comment = "mentioning users ~mention1, ~mention2, and ~mention3 in a comment"

    assert find_mentioned_users(comment) == set()

    u1 = UserFactory(username="mention1")
    db.session.commit()
    assert find_mentioned_users(comment) == {u1}

    u2 = UserFactory(username="mention2")
    db.session.commit()
    assert find_mentioned_users(comment) == {u1, u2}

    u3 = UserFactory(username="mention3")
    db.session.commit()
    assert find_mentioned_users(comment) == {u1, u2, u3}
