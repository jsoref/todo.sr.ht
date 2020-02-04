import pytest

from tests import factories as f
from todosrht.search import apply_search
from todosrht.types import Ticket, TicketStatus
from srht.database import db


def test_ticket_search(client):
    owner = f.UserFactory()
    tracker = f.TrackerFactory(owner=owner)

    luke = f.ParticipantFactory(user=f.UserFactory(username="luke"))
    leia = f.ParticipantFactory(user=f.UserFactory(username="leia"))
    han = f.ParticipantFactory(user=f.UserFactory(username="han"))

    ticket1 = f.TicketFactory(
        tracker=tracker,
        title="title_1 used_to_test_or",
        description="description_1 lightsabre",
        submitter=han,
    )

    ticket2 = f.TicketFactory(
        tracker=tracker,
        title="title_2",
        description="description_2 blaster used_to_test_or",
        submitter=han,
    )

    ticket3 = f.TicketFactory(
        tracker=tracker,
        title="title_3",
        description="description_3 lightsabre",
        submitter=luke,
    )

    ticket4 = f.TicketFactory(
        tracker=tracker,
        title="title_4",
        description="description_4 blaster",
        submitter=leia,
    )

    ticket5 = f.TicketFactory(
        tracker=tracker,
        title="title_5",
        description="description_5 lightsabre",
        submitter=leia,
    )

    # Assignees
    f.TicketAssigneeFactory(ticket=ticket1, assignee=luke.user, assigner=owner)
    f.TicketAssigneeFactory(ticket=ticket2, assignee=luke.user, assigner=owner)
    f.TicketAssigneeFactory(ticket=ticket2, assignee=leia.user, assigner=owner)
    f.TicketAssigneeFactory(ticket=ticket3, assignee=leia.user, assigner=owner)

    # Labels
    jedi = f.LabelFactory(tracker=tracker, name="jedi")
    sith = f.LabelFactory(tracker=tracker, name="sith")

    f.TicketLabelFactory(user=owner, ticket=ticket1, label=jedi)
    f.TicketLabelFactory(user=owner, ticket=ticket2, label=sith)
    f.TicketLabelFactory(user=owner, ticket=ticket5, label=jedi)
    f.TicketLabelFactory(user=owner, ticket=ticket5, label=sith)

    # Comments
    f.TicketCommentFactory(ticket=ticket1, submitter=luke,
        text="May the force be with you!")
    f.TicketCommentFactory(ticket=ticket1, submitter=han,
        text="“It’s the ship that made the Kessel Run in less than twelve parsecs!")
    f.TicketCommentFactory(ticket=ticket3, submitter=leia,
        text="This comment is used_to_test_or")

    db.session.commit()

    query = Ticket.query.filter(Ticket.tracker_id == tracker.id)

    def search(search_string, user=owner):
        return apply_search(query, search_string, user).all()

    # Search by title (only returns open tickets by default)
    assert search("title_1") == [ticket1]
    assert search("title_2") == [ticket2]
    assert search("title_3") == [ticket3]
    assert search("title_4") == [ticket4]
    assert search("title_5") == [ticket5]

    assert search("title_1 title_2") == []

    # Search by description
    assert search("description_1") == [ticket1]
    assert search("description_2") == [ticket2]
    assert search("description_3") == [ticket3]
    assert search("description_4") == [ticket4]
    assert search("description_5") == [ticket5]

    assert search("lightsabre") == [ticket1, ticket3, ticket5]
    assert search("blaster") == [ticket2, ticket4]

    # Search by comment
    assert search("parsecs") == [ticket1]

    # Order of words does not matter
    assert search("may the force be with you") == [ticket1]
    assert search("the force may with you be") == [ticket1]

    # Except when in quotes
    assert search("'may the force be with you'") == [ticket1]
    assert search("'force may with you be'") == []

    # Search either title, description, or comment
    assert search("used_to_test_or") == [ticket1, ticket2, ticket3]

    # Search by submitter
    assert search("submitter:luke") == [ticket3]
    assert search("submitter:leia") == [ticket4, ticket5]
    assert search("submitter:han") == [ticket1, ticket2]

    assert search("!submitter:luke") == [ticket1, ticket2, ticket4, ticket5]
    assert search("!submitter:leia") == [ticket1, ticket2, ticket3]
    assert search("!submitter:han") == [ticket3, ticket4, ticket5]

    # Search by asignee
    assert search("assigned:luke") == [ticket1, ticket2]
    assert search("assigned:leia") == [ticket2, ticket3]
    assert search("!assigned:luke") == [ticket3, ticket4, ticket5]
    assert search("!assigned:leia") == [ticket1, ticket4, ticket5]
    assert search("assigned:luke assigned:leia") == [ticket2]
    assert search("assigned:luke !assigned:leia") == [ticket1]
    assert search("!assigned:luke assigned:leia") == [ticket3]
    assert search("!assigned:luke !assigned:leia") == [ticket4, ticket5]

    assert search("no:assignee") == [ticket4, ticket5]
    assert search("!no:assignee") == [ticket1, ticket2, ticket3]

    with pytest.raises(ValueError) as excinfo:
        search("no:foo")
    assert "Invalid search term: 'no:foo'" == str(excinfo.value)

    assert search("assigned:me") == []
    assert search("assigned:me", han.user) == []
    assert search("assigned:me", luke.user) == [ticket1, ticket2]
    assert search("assigned:me", leia.user) == [ticket2, ticket3]

    assert search("!assigned:me") == [ticket1, ticket2, ticket3, ticket4, ticket5]
    assert search("!assigned:me", han.user) == [ticket1, ticket2, ticket3, ticket4, ticket5]
    assert search("!assigned:me", luke.user) == [ticket3, ticket4, ticket5]
    assert search("!assigned:me", leia.user) == [ticket1, ticket4, ticket5]

    # Search by label
    assert search("label:jedi") == [ticket1, ticket5]
    assert search("label:sith") == [ticket2, ticket5]
    assert search("!label:jedi") == [ticket2, ticket3, ticket4]
    assert search("!label:sith") == [ticket1, ticket3, ticket4]
    assert search("label:jedi label:sith") == [ticket5]

    assert search("no:label") == [ticket3, ticket4]
    assert search("!no:label") == [ticket1, ticket2, ticket5]

    # Combinations
    assert search(
        "title_1 description_1 force with you label:jedi !label:sith "
        "assigned:luke !assigned:me"
    ) == [ticket1]

def test_ticket_search_by_status(client):
    owner = f.UserFactory()
    submitter = f.ParticipantFactory(user=owner)
    tracker = f.TrackerFactory(owner=owner)

    defaults = {"tracker": tracker, "submitter": submitter}

    ticket1 = f.TicketFactory(**defaults, status=TicketStatus.reported)
    ticket2 = f.TicketFactory(**defaults, status=TicketStatus.confirmed)
    ticket3 = f.TicketFactory(**defaults, status=TicketStatus.in_progress)
    ticket4 = f.TicketFactory(**defaults, status=TicketStatus.pending)
    ticket5 = f.TicketFactory(**defaults, status=TicketStatus.resolved)

    db.session.commit()

    query = Ticket.query.filter(Ticket.tracker_id == tracker.id)

    def search(search_string, user=owner):
        return apply_search(query, search_string, user).all()

    assert search("") == [ticket1, ticket2, ticket3, ticket4]
    assert search("status:any") == [ticket1, ticket2, ticket3, ticket4, ticket5]
    assert search("status:open") == [ticket1, ticket2, ticket3, ticket4]
    assert search("status:closed") == [ticket5]

    assert search("!status:any") == []
    assert search("!status:open") == [ticket5]
    assert search("!status:closed") == [ticket1, ticket2, ticket3, ticket4]

    assert search("status:reported") == [ticket1]
    assert search("status:confirmed") == [ticket2]
    assert search("status:in_progress") == [ticket3]
    assert search("status:pending") == [ticket4]
    assert search("status:resolved") == [ticket5]

    assert search("!status:reported") == [ticket2, ticket3, ticket4, ticket5]
    assert search("!status:confirmed") == [ticket1, ticket3, ticket4, ticket5]
    assert search("!status:in_progress") == [ticket1, ticket2, ticket4, ticket5]
    assert search("!status:pending") == [ticket1, ticket2, ticket3, ticket5]
    assert search("!status:resolved") == [ticket1, ticket2, ticket3, ticket4]

    with pytest.raises(ValueError) as excinfo:
        search("status:foo")
    assert str(excinfo.value) == "Invalid status: 'foo'"
