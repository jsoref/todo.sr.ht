import pytest
import re

from srht.database import db
from todosrht.tickets import add_comment
from todosrht.tickets import find_mentioned_users, find_mentioned_tickets
from todosrht.tickets import USER_MENTION_PATTERN, TICKET_MENTION_PATTERN
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


def test_user_mention_pattern():
    def match(text):
        return re.findall(USER_MENTION_PATTERN, text)

    assert match("mentioning ~u1, ~u2, and ~u3 here") == ['u1', 'u2', 'u3']
    assert match("~user at start") == ['user']
    assert match("in ~user middle") == ['user']
    assert match("at end ~user.") == ['user']

    assert match("no leading whitespace~user") == []
    assert match("double tilde ~~user") == []
    assert match("other leading chars #~user /~user \\~user") == []

    # Should not match URLs containing usernames
    # https://todo.sr.ht/~sircmpwn/todo.sr.ht/162
    assert match("~user1 and https://todo.sr.ht/~user2") == ['user1']
    assert match("~user1 and https://todo.sr.ht/~user2/tracker") == ['user1']

    # Should not match usernames in qualified ticket mentions
    assert match("~user1/repo#123") == []


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


def test_notifications_and_events(mailbox):
    u1 = UserFactory()
    u2 = UserFactory()
    u3 = UserFactory()  # not mentioned

    commenter = UserFactory()
    ticket = TicketFactory()

    t1 = TicketFactory(tracker=ticket.tracker)
    t2 = TicketFactory(tracker=ticket.tracker)
    t3 = TicketFactory(tracker=ticket.tracker)  # not mentioned

    db.session.flush()

    text = (
        f"mentioning users {u1.canonical_name}, ~doesnotexist, "
        f"and {u2.canonical_name} "
        f"also mentioning tickets #{t1.scoped_id}, and #{t2.scoped_id} and #999999"
    )
    comment = add_comment(commenter, ticket, text)

    assert len(mailbox) == 2

    email1 = next(e for e in mailbox if e.to == u1.email)
    email2 = next(e for e in mailbox if e.to == u2.email)

    expected_title = f"{ticket.ref()}: {ticket.title}"
    expected_body = f"You were mentioned in {ticket.ref()} by {commenter}."

    assert email1.subject == expected_title
    assert email1.body.startswith(expected_body)

    assert email2.subject == expected_title
    assert email2.body.startswith(expected_body)

    # Check correct events are generated
    comment_events = {e for e in ticket.events
        if e.event_type == EventType.comment}
    user_events = {e for e in ticket.events
        if e.event_type == EventType.user_mentioned}

    assert len(comment_events) == 1
    assert len(user_events) == 2

    u1_mention = next(e for e in user_events if e.user == u1)
    u2_mention = next(e for e in user_events if e.user == u2)

    assert u1_mention.comment == comment
    assert u1_mention.ticket == ticket

    assert u2_mention.comment == comment
    assert u2_mention.ticket == ticket

    assert len(t1.events) == 1
    assert len(t2.events) == 1
    assert len(t3.events) == 0

    t1_mention = t1.events[0]
    t2_mention = t2.events[0]

    assert t1_mention.comment == comment
    assert t1_mention.user == commenter

    assert t2_mention.comment == comment
    assert t2_mention.user == commenter

def test_ticket_mention_pattern():
    def match(text):
        return re.findall(TICKET_MENTION_PATTERN, text)

    assert match("#1, #13, and #372") == [
        ('', '', '', '1'),
        ('', '', '', '13'),
        ('', '', '', '372')
    ]

    assert match("some#1, other#13, and trackers#372") == [
        ('', '', 'some', '1'),
        ('', '', 'other', '13'),
        ('', '', 'trackers', '372')
    ]

    assert match("~foo/some#1, ~bar/other#13, and ~baz/trackers#372") == [
        ('~foo/', 'foo', 'some', '1'),
        ('~bar/', 'bar', 'other', '13'),
        ('~baz/', 'baz', 'trackers', '372')
    ]

    # "Special" chars in username and tracker name
    assert match("~foo_bar_1/some-funky_tracker.name._-2#1") == [
        ('~foo_bar_1/', 'foo_bar_1', 'some-funky_tracker.name._-2', '1')
    ]

def test_find_mentioned_tickets():
    u1 = UserFactory()
    tr1 = TrackerFactory(owner=u1)
    t11 = TicketFactory(tracker=tr1, scoped_id=1)
    t12 = TicketFactory(tracker=tr1, scoped_id=13)

    tr2 = TrackerFactory(owner=u1)
    t21 = TicketFactory(tracker=tr2, scoped_id=1)
    t22 = TicketFactory(tracker=tr2, scoped_id=42)

    u3 = UserFactory()
    tr3 = TrackerFactory(owner=u3)
    t31 = TicketFactory(tracker=tr3, scoped_id=1)
    t32 = TicketFactory(tracker=tr3, scoped_id=442)

    db.session.commit()

    # Texts with no matching ticket mentions
    texts = [
        "Nothing to see here, move along",
        "Do not exist: #500, foo#300, ~bar/foo#123",
        f"Also do not exist: {u1}/{tr1.name}#42, {u1}/{tr1.name}#442",
    ]
    for text in texts:
        for tr in [tr1, tr2, tr3]:
            assert find_mentioned_tickets(tr, text) == set()

    # Mentioning ticket by number only matches tickets in the same tracker
    text = "winning tickets are: #1, #13 and #42"
    assert find_mentioned_tickets(tr1, text) == {t11, t12}
    assert find_mentioned_tickets(tr2, text) == {t21, t22}
    assert find_mentioned_tickets(tr3, text) == {t31}

    # Mentioning ticket by number and tracker name matches tickets in the
    # repository with the given name, owned by the same user as the repository
    # on which the comment is posted
    text = f"winning tickets are: {tr1.name}#1, {tr1.name}#13 and {tr1.name}#42"
    assert find_mentioned_tickets(tr1, text) == {t11, t12}
    assert find_mentioned_tickets(tr2, text) == {t11, t12}
    assert find_mentioned_tickets(tr3, text) == set()  # owned by u3

    text = f"winning tickets are: {tr2.name}#1, {tr2.name}#13 and {tr2.name}#42"
    assert find_mentioned_tickets(tr1, text) == {t21, t22}
    assert find_mentioned_tickets(tr2, text) == {t21, t22}
    assert find_mentioned_tickets(tr3, text) == set()  # owned by u3

    text = f"winning tickets are: {tr3.name}#1, {tr3.name}#13 and {tr3.name}#42"
    assert find_mentioned_tickets(tr1, text) == set()  # owned by u1
    assert find_mentioned_tickets(tr2, text) == set()  # owned by u1
    assert find_mentioned_tickets(tr3, text) == {t31}

    # Fully qualified mentions include user, tracker and ticket ID
    for tr in [tr1, tr2, tr3]:
        for t in [t11, t12, t21, t22, t31, t32]:
            assert find_mentioned_tickets(tr, f"mentioning {t.ref()}") == {t}
