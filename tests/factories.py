import factory
from datetime import datetime, timedelta
from factory.fuzzy import FuzzyText
from srht.database import db
from todosrht.types import Tracker, User, Ticket

future_datetime = datetime.now() + timedelta(days=10)


class UserFactory(factory.alchemy.SQLAlchemyModelFactory):
    id = factory.Sequence(lambda n: n)
    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.Sequence(lambda n: f"user{n}@example.com")
    oauth_token = FuzzyText(length=32)
    oauth_token_expires = future_datetime
    oauth_token_scopes = "profile:read"
    oauth_revocation_token = "rev-token"

    class Meta:
        model = User
        sqlalchemy_session = db.session


class TrackerFactory(factory.alchemy.SQLAlchemyModelFactory):
    id = factory.Sequence(lambda n: n)
    owner = factory.SubFactory(UserFactory)
    name = factory.Sequence(lambda n: f"tracker{n}")

    class Meta:
        model = Tracker
        sqlalchemy_session = db.session


class TicketFactory(factory.alchemy.SQLAlchemyModelFactory):
    id = factory.Sequence(lambda n: n)
    tracker = factory.SubFactory(TrackerFactory)
    scoped_id = factory.Sequence(lambda n: n)
    submitter = factory.SubFactory(UserFactory)
    title = "A wild ticket appeared"

    class Meta:
        model = Ticket
        sqlalchemy_session = db.session
