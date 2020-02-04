import factory
from datetime import datetime, timedelta
from factory.fuzzy import FuzzyText
from srht.database import db
from todosrht.types import Tracker, User, Ticket, Participant, ParticipantType
from todosrht.types import Label, TicketLabel, TicketAssignee, TicketComment

future_datetime = datetime.now() + timedelta(days=10)


class UserFactory(factory.alchemy.SQLAlchemyModelFactory):
    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.Sequence(lambda n: f"user{n}@example.com")
    oauth_token = FuzzyText(length=32)
    oauth_token_expires = future_datetime
    oauth_token_scopes = "profile:read"
    oauth_revocation_token = "rev-token"

    class Meta:
        model = User
        sqlalchemy_session = db.session


class ParticipantFactory(factory.alchemy.SQLAlchemyModelFactory):
    participant_type = ParticipantType.user
    user = factory.SubFactory(UserFactory)

    class Meta:
        model = Participant
        sqlalchemy_session = db.session


class TrackerFactory(factory.alchemy.SQLAlchemyModelFactory):
    owner = factory.SubFactory(UserFactory)
    name = factory.Sequence(lambda n: f"tracker{n}")
    import_in_progress = False

    class Meta:
        model = Tracker
        sqlalchemy_session = db.session


class TicketFactory(factory.alchemy.SQLAlchemyModelFactory):
    tracker = factory.SubFactory(TrackerFactory)
    scoped_id = factory.Sequence(lambda n: n)
    submitter = factory.SubFactory(ParticipantFactory)
    title = "A wild ticket appeared"

    class Meta:
        model = Ticket
        sqlalchemy_session = db.session


class LabelFactory(factory.alchemy.SQLAlchemyModelFactory):
    tracker = factory.SubFactory(TrackerFactory)
    color = "#ffffff"
    text_color = "#000000"

    class Meta:
        model = Label
        sqlalchemy_session = db.session


class TicketLabelFactory(factory.alchemy.SQLAlchemyModelFactory):
    ticket = factory.SubFactory(TicketFactory)
    label = factory.SubFactory(LabelFactory)
    user = factory.SubFactory(UserFactory)

    class Meta:
        model = TicketLabel
        sqlalchemy_session = db.session


class TicketAssigneeFactory(factory.alchemy.SQLAlchemyModelFactory):
    ticket = factory.SubFactory(TicketFactory)
    assignee = factory.SubFactory(UserFactory)
    assigner = factory.SubFactory(UserFactory)

    class Meta:
        model = TicketAssignee
        sqlalchemy_session = db.session

class TicketCommentFactory(factory.alchemy.SQLAlchemyModelFactory):
    ticket = factory.SubFactory(TicketFactory)
    submitter = factory.SubFactory(ParticipantFactory)
    text = "This is a helpful comment."

    class Meta:
        model = TicketComment
        sqlalchemy_session = db.session
