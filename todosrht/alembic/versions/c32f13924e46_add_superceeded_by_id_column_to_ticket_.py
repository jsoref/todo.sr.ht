"""Add superceeded_by_id column to ticket comment

Revision ID: c32f13924e46
Revises: 074182407bb2
Create Date: 2020-08-25 15:28:19.574915

"""

# revision identifiers, used by Alembic.
revision = 'c32f13924e46'
down_revision = '074182407bb2'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column("ticket_comment", sa.Column("superceeded_by_id",
        sa.Integer, sa.ForeignKey("ticket_comment.id", ondelete="SET NULL")))


def downgrade():
    op.drop_column("ticket_comment", "superceeded_by_id")
