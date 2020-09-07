"""Add core.sr.ht cascades to tracker & ticket webhooks

Revision ID: 6c714f704591
Revises: 6742af305c73
Create Date: 2020-09-07 12:42:28.500857

"""

# revision identifiers, used by Alembic.
revision = '6c714f704591'
down_revision = '6742af305c73'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.drop_constraint(
            constraint_name="tracker_webhook_subscription_token_id_fkey",
            table_name="tracker_webhook_subscription",
            type_="foreignkey")
    op.create_foreign_key(
            constraint_name="tracker_webhook_subscription_token_id_fkey",
            source_table="tracker_webhook_subscription",
            referent_table="oauthtoken",
            local_cols=["token_id"],
            remote_cols=["id"],
            ondelete="CASCADE")
    op.drop_constraint(
            constraint_name="tracker_webhook_subscription_user_id_fkey",
            table_name="tracker_webhook_subscription",
            type_="foreignkey")
    op.create_foreign_key(
            constraint_name="tracker_webhook_subscription_user_id_fkey",
            source_table="tracker_webhook_subscription",
            referent_table="user",
            local_cols=["user_id"],
            remote_cols=["id"],
            ondelete="CASCADE")

    op.drop_constraint(
            constraint_name="ticket_webhook_subscription_token_id_fkey",
            table_name="ticket_webhook_subscription",
            type_="foreignkey")
    op.create_foreign_key(
            constraint_name="ticket_webhook_subscription_token_id_fkey",
            source_table="ticket_webhook_subscription",
            referent_table="oauthtoken",
            local_cols=["token_id"],
            remote_cols=["id"],
            ondelete="CASCADE")
    op.drop_constraint(
            constraint_name="ticket_webhook_subscription_user_id_fkey",
            table_name="ticket_webhook_subscription",
            type_="foreignkey")
    op.create_foreign_key(
            constraint_name="ticket_webhook_subscription_user_id_fkey",
            source_table="ticket_webhook_subscription",
            referent_table="user",
            local_cols=["user_id"],
            remote_cols=["id"],
            ondelete="CASCADE")


def downgrade():
    op.drop_constraint(
            constraint_name="tracker_webhook_subscription_token_id_fkey",
            table_name="tracker_webhook_subscription",
            type_="foreignkey")
    op.create_foreign_key(
            constraint_name="tracker_webhook_subscription_token_id_fkey",
            source_table="tracker_webhook_subscription",
            referent_table="oauthtoken",
            local_cols=["token_id"],
            remote_cols=["id"],
            ondelete="CASCADE")
    op.drop_constraint(
            constraint_name="tracker_webhook_subscription_user_id_fkey",
            table_name="tracker_webhook_subscription",
            type_="foreignkey")
    op.create_foreign_key(
            constraint_name="tracker_webhook_subscription_user_id_fkey",
            source_table="tracker_webhook_subscription",
            referent_table="user",
            local_cols=["user_id"],
            remote_cols=["id"])

    op.drop_constraint(
            constraint_name="ticket_webhook_subscription_token_id_fkey",
            table_name="ticket_webhook_subscription",
            type_="foreignkey")
    op.create_foreign_key(
            constraint_name="ticket_webhook_subscription_token_id_fkey",
            source_table="ticket_webhook_subscription",
            referent_table="oauthtoken",
            local_cols=["token_id"],
            remote_cols=["id"])
    op.drop_constraint(
            constraint_name="ticket_webhook_subscription_user_id_fkey",
            table_name="ticket_webhook_subscription",
            type_="foreignkey")
    op.create_foreign_key(
            constraint_name="ticket_webhook_subscription_user_id_fkey",
            source_table="ticket_webhook_subscription",
            referent_table="user",
            local_cols=["user_id"],
            remote_cols=["id"],
            ondelete="CASCADE")
