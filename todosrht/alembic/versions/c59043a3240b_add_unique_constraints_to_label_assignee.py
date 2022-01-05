"""Add unique constraints to label & assignee

Revision ID: c59043a3240b
Revises: ce5b2bdc66fe
Create Date: 2022-01-05 12:20:23.652965

"""

# revision identifiers, used by Alembic.
revision = 'c59043a3240b'
down_revision = 'ce5b2bdc66fe'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.execute("""
    ALTER TABLE ticket_assignee
    DROP COLUMN role,
    ADD CONSTRAINT idx_ticket_assignee_unique UNIQUE (ticket_id, assignee_id);
    """)


def downgrade():
    op.execute("""
    ALTER TABLE ticket_assignee
    ADD COLUMN role character varying(256),
    DROP CONSTRAINT idx_ticket_assignee_unique;
    """)
