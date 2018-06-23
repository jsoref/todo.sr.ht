"""clear defaults from tickets to support tracker perms

Revision ID: cb9732f3364c
Revises: 6169a5600336
Create Date: 2017-12-08 00:11:44.296523

"""

# revision identifiers, used by Alembic.
revision = 'cb9732f3364c'
down_revision = '6169a5600336'

from alembic import op
import sqlalchemy as sa

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

Session = sessionmaker()
Base = declarative_base()

from enum import IntFlag

class TicketAccess(IntFlag):
    none = 0
    browse = 1
    submit = 2
    comment = 4
    edit = 8
    triage = 16
    all = browse | submit | comment | edit | triage

import sqlalchemy.types as types
from srht.flagtype import FlagType

class Ticket(Base):
    __tablename__ = 'ticket'
    id = sa.Column(sa.Integer, primary_key=True)
    scoped_id = sa.Column(sa.Integer)
    tracker_id = sa.Column(sa.Integer, sa.ForeignKey("tracker.id"), nullable=False)
    tracker = sa.orm.relationship("Tracker")

    user_perms = sa.Column(FlagType(TicketAccess), nullable=True)
    submitter_perms = sa.Column(FlagType(TicketAccess), nullable=True)
    committer_perms = sa.Column(FlagType(TicketAccess), nullable=True)
    anonymous_perms = sa.Column(FlagType(TicketAccess), nullable=True)

class Tracker(Base):
    __tablename__ = 'tracker'
    id = sa.Column(sa.Integer, primary_key=True)
    next_ticket_id = sa.Column(sa.Integer, nullable=False, default=1)

    default_user_perms = sa.Column(FlagType(TicketAccess), nullable=False)
    default_submitter_perms = sa.Column(FlagType(TicketAccess), nullable=False)
    default_committer_perms = sa.Column(FlagType(TicketAccess), nullable=False)
    default_anonymous_perms = sa.Column(FlagType(TicketAccess), nullable=False)


def upgrade():
    op.alter_column("ticket", "user_perms", nullable=True)
    op.alter_column("ticket", "submitter_perms", nullable=True)
    op.alter_column("ticket", "committer_perms", nullable=True)
    op.alter_column("ticket", "anonymous_perms", nullable=True)

    bind = op.get_bind()
    session = sessionmaker()(bind=bind)

    for ticket in session.query(Ticket):
        if ticket.anonymous_perms == ticket.tracker.default_anonymous_perms:
            ticket.anonymous_perms = None
        if ticket.user_perms == ticket.tracker.default_user_perms:
            ticket.user_perms = None
        if ticket.submitter_perms == ticket.tracker.default_submitter_perms:
            ticket.submitter_perms = None
        if ticket.committer_perms == ticket.tracker.default_committer_perms:
            ticket.committer_perms = None
    session.commit()


def downgrade():
    bind = op.get_bind()
    session = sessionmaker()(bind=bind)
    for ticket in session.query(Ticket):
        ticket.anonymous_perms = ticket.tracker.default_anonymous_perms
        ticket.user_perms = ticket.tracker.default_user_perms
        ticket.submitter_perms = ticket.tracker.default_submitter_perms
        ticket.committer_perms = ticket.tracker.default_committer_perms
    session.commit()

    op.alter_column("ticket", "user_perms", nullable=False)
    op.alter_column("ticket", "submitter_perms", nullable=False)
    op.alter_column("ticket", "committer_perms", nullable=False)
    op.alter_column("ticket", "anonymous_perms", nullable=False)
