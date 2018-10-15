"""Add ticket_label

Revision ID: cf222857edec
Revises: 3a0a7407fb50
Create Date: 2018-10-11 15:21:44.218379

"""

# revision identifiers, used by Alembic.
revision = 'cf222857edec'
down_revision = '3a0a7407fb50'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('ticket_label',
        sa.Column('ticket_id', sa.Integer(), nullable=False),
        sa.Column('label_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('created', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['label_id'], ['label.id']),
        sa.ForeignKeyConstraint(['ticket_id'], ['ticket.id']),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('ticket_id', 'label_id')
    )


def downgrade():
    op.drop_table('ticket_label')
