"""Drop user_agent from tickets

Revision ID: bdf809d6a775
Revises: bd06de76eb15
Create Date: 2018-12-14 10:17:07.041567

"""

# revision identifiers, used by Alembic.
revision = 'bdf809d6a775'
down_revision = 'bd06de76eb15'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.drop_column('ticket', 'user_agent')


def downgrade():
    op.add_column('ticket', sa.Column('user_agent', sa.Unicode(2048)))
