"""Add label

Revision ID: 3a0a7407fb50
Revises: cb9732f3364c
Create Date: 2018-10-08 16:48:16.900142

"""

# revision identifiers, used by Alembic.
revision = '3a0a7407fb50'
down_revision = 'cb9732f3364c'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('label',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created', sa.DateTime(), nullable=False),
        sa.Column('updated', sa.DateTime(), nullable=False),
        sa.Column('tracker_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('color', sa.Text(), nullable=False),
        sa.Column('text_color', sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(['tracker_id'], ['tracker.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tracker_id', 'name', name='idx_tracker_name_unique')
    )


def downgrade():
    op.drop_table('label')
