"""Add user.remote_id

Revision ID: b5f503ac3ae9
Revises: e1e2e901be0c
Create Date: 2022-06-16 10:11:00.727683

"""

# revision identifiers, used by Alembic.
revision = 'b5f503ac3ae9'
down_revision = 'e1e2e901be0c'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from srht.crypto import internal_anon
from srht.database import db
from srht.graphql import exec_gql

Base = declarative_base()

class User(Base):
    __tablename__ = "user"
    id = sa.Column(sa.Integer, primary_key=True)
    username = sa.Column(sa.Unicode(256), index=True, unique=True)
    remote_id = sa.Column(sa.Integer, unique=True)

def upgrade():
    engine = op.get_bind()
    session = scoped_session(sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine))
    Base.query = session.query_property()

    op.execute("""ALTER TABLE "user" ADD COLUMN remote_id integer UNIQUE""")

    for user in User.query:
        user.remote_id = fetch_user_id(user.username)
        print(f"~{user.username} id: {user.id} -> {user.remote_id}")
    session.commit()

    op.execute("""ALTER TABLE "user" ALTER COLUMN remote_id SET NOT NULL""")

def downgrade():
    op.drop_column("user", "remote_id")

def fetch_user_id(username):
    resp = exec_gql("meta.sr.ht",
            "query($username: String!) { user(username: $username) { id } }",
            user=internal_anon,
            username=username)
    return resp["user"]["id"]
