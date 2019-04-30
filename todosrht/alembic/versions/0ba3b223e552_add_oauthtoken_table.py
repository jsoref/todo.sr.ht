"""Add OAuthToken table

Revision ID: 0ba3b223e552
Revises: 75ff2f7624fd
Create Date: 2019-04-30 14:13:01.065669

"""

# revision identifiers, used by Alembic.
revision = '0ba3b223e552'
down_revision = '75ff2f7624fd'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('oauthtoken',
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("created", sa.DateTime, nullable=False),
        sa.Column("updated", sa.DateTime, nullable=False),
        sa.Column("expires", sa.DateTime, nullable=False),
        sa.Column("token_hash", sa.String(128), nullable=False),
        sa.Column("token_partial", sa.String(8), nullable=False),
        sa.Column("scopes", sa.String(512), nullable=False),
        sa.Column("user_id", sa.Integer, sa.ForeignKey('user.id')))


def downgrade():
    op.drop_table('oauthtoken')
