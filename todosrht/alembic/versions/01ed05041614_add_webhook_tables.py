"""Add webhook tables

Revision ID: 01ed05041614
Revises: 0ba3b223e552
Create Date: 2019-06-10 12:41:12.558191

"""

# revision identifiers, used by Alembic.
revision = '01ed05041614'
down_revision = '0ba3b223e552'

from alembic import op
import sqlalchemy as sa
import sqlalchemy_utils as sau


def upgrade():
    op.create_table('user_webhook_subscription',
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("created", sa.DateTime, nullable=False),
        sa.Column("url", sa.Unicode(2048), nullable=False),
        sa.Column("events", sa.Unicode, nullable=False),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("user.id")),
        sa.Column("token_id", sa.Integer, sa.ForeignKey("oauthtoken.id")),
    )
    op.create_table('user_webhook_delivery',
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("uuid", sau.UUIDType, nullable=False),
        sa.Column("created", sa.DateTime, nullable=False),
        sa.Column("event", sa.Unicode(256), nullable=False),
        sa.Column("url", sa.Unicode(2048), nullable=False),
        sa.Column("payload", sa.Unicode(65536), nullable=False),
        sa.Column("payload_headers", sa.Unicode(16384), nullable=False),
        sa.Column("response", sa.Unicode(65536)),
        sa.Column("response_status", sa.Integer, nullable=False),
        sa.Column("response_headers", sa.Unicode(16384)),
        sa.Column("subscription_id", sa.Integer,
            sa.ForeignKey('user_webhook_subscription.id'), nullable=False),
    )
    op.create_table('tracker_webhook_subscription',
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("created", sa.DateTime, nullable=False),
        sa.Column("url", sa.Unicode(2048), nullable=False),
        sa.Column("events", sa.Unicode, nullable=False),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("user.id")),
        sa.Column("token_id", sa.Integer, sa.ForeignKey("oauthtoken.id")),
        sa.Column("tracker_id", sa.Integer, sa.ForeignKey('tracker.id'),
            nullable=False)
    )
    op.create_table('tracker_webhook_delivery',
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("uuid", sau.UUIDType, nullable=False),
        sa.Column("created", sa.DateTime, nullable=False),
        sa.Column("event", sa.Unicode(256), nullable=False),
        sa.Column("url", sa.Unicode(2048), nullable=False),
        sa.Column("payload", sa.Unicode(65536), nullable=False),
        sa.Column("payload_headers", sa.Unicode(16384), nullable=False),
        sa.Column("response", sa.Unicode(65536)),
        sa.Column("response_status", sa.Integer, nullable=False),
        sa.Column("response_headers", sa.Unicode(16384)),
        sa.Column("subscription_id", sa.Integer,
            sa.ForeignKey('tracker_webhook_subscription.id'), nullable=False),
    )
    op.create_table('ticket_webhook_subscription',
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("created", sa.DateTime, nullable=False),
        sa.Column("url", sa.Unicode(2048), nullable=False),
        sa.Column("events", sa.Unicode, nullable=False),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("user.id")),
        sa.Column("token_id", sa.Integer, sa.ForeignKey("oauthtoken.id")),
        sa.Column("ticket_id", sa.Integer, sa.ForeignKey('ticket.id'),
            nullable=False)
    )
    op.create_table('ticket_webhook_delivery',
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("uuid", sau.UUIDType, nullable=False),
        sa.Column("created", sa.DateTime, nullable=False),
        sa.Column("event", sa.Unicode(256), nullable=False),
        sa.Column("url", sa.Unicode(2048), nullable=False),
        sa.Column("payload", sa.Unicode(65536), nullable=False),
        sa.Column("payload_headers", sa.Unicode(16384), nullable=False),
        sa.Column("response", sa.Unicode(65536)),
        sa.Column("response_status", sa.Integer, nullable=False),
        sa.Column("response_headers", sa.Unicode(16384)),
        sa.Column("subscription_id", sa.Integer,
            sa.ForeignKey('ticket_webhook_subscription.id'), nullable=False),
    )


def downgrade():
    sa.drop_table('ticket_webhook_delivery')
    sa.drop_table('ticket_webhook_subscription')
    sa.drop_table('tracker_webhook_delivery')
    sa.drop_table('tracker_webhook_subscription')
    sa.drop_table('user_webhook_delivery')
    sa.drop_table('user_webhook_subscription')
