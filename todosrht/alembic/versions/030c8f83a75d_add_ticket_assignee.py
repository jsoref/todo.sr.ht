"""Add ticket_assignee.

Revision ID: 030c8f83a75d
Revises: a8cb241798dc
Create Date: 2018-11-29 12:49:32.945127

"""

# revision identifiers, used by Alembic.
revision = '030c8f83a75d'
down_revision = 'a8cb241798dc'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('ticket_assignee',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created', sa.DateTime(), nullable=False),
        sa.Column('updated', sa.DateTime(), nullable=False),
        sa.Column('ticket_id', sa.Integer(), nullable=False),
        sa.Column('assignee_id', sa.Integer(), nullable=False),
        sa.Column('assigner_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.Unicode(length=256), nullable=True),
        sa.ForeignKeyConstraint(['assignee_id'], ['user.id'], ),
        sa.ForeignKeyConstraint(['assigner_id'], ['user.id'], ),
        sa.ForeignKeyConstraint(['ticket_id'], ['ticket.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('ticket_assignee')
