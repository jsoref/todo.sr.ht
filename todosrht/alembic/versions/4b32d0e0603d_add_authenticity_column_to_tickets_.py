"""Add authenticity column to tickets & comments

Revision ID: 4b32d0e0603d
Revises: 4631a2317dd0
Create Date: 2020-01-09 09:39:26.614899

"""

# revision identifiers, used by Alembic.
revision = '4b32d0e0603d'
down_revision = '4631a2317dd0'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column("ticket", sa.Column("authenticity", sa.Integer,
            nullable=False, server_default="0"))
    op.add_column("ticket_comment", sa.Column("authenticity", sa.Integer,
            nullable=False, server_default="0"))
    op.add_column("tracker", sa.Column("import_in_progress", sa.Boolean,
            nullable=False, server_default="f"))

def downgrade():
    op.drop_column("ticket", "authenticity")
    op.drop_column("ticket_comment", "authenticity")
    op.drop_column("tracker", "import_in_progress")
