"""Link event to label

Revision ID: a8cb241798dc
Revises: cf222857edec
Create Date: 2018-10-18 16:21:54.739215

"""

# revision identifiers, used by Alembic.
revision = 'a8cb241798dc'
down_revision = 'cf222857edec'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('event', sa.Column('label_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'event', 'label', ['label_id'], ['id'])


def downgrade():
    op.drop_constraint(None, 'event', type_='foreignkey')
    op.drop_column('event', 'label_id')
