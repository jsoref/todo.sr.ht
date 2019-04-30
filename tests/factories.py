import factory
from datetime import datetime, timedelta
from factory.fuzzy import FuzzyText
from srht.database import db
from srht.validation import Validation
from todosrht.types import Tracker, User, Ticket

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


class TrackerFactory(factory.alchemy.SQLAlchemyModelFactory):
    user = factory.SubFactory(UserFactory)
    valid = factory.Sequence(lambda n: Validation({ "name": f"tracker{n}" }))

    class Meta:
        model = Tracker
        sqlalchemy_session = db.session


class TicketFactory(factory.alchemy.SQLAlchemyModelFactory):
    tracker = factory.SubFactory(TrackerFactory)
    scoped_id = factory.Sequence(lambda n: n)
    submitter = factory.SubFactory(UserFactory)
    title = "A wild ticket appeared"

    class Meta:
        model = Ticket
        sqlalchemy_session = db.session
