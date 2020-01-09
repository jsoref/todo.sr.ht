"""Add cascade to tracker & ticket webhooks

Revision ID: 61e241dc978c
Revises: 4b32d0e0603d
Create Date: 2020-01-09 10:38:42.203433

"""

# revision identifiers, used by Alembic.
revision = '61e241dc978c'
down_revision = '4b32d0e0603d'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.drop_constraint(
            constraint_name="tracker_webhook_subscription_tracker_id_fkey",
            table_name="tracker_webhook_subscription",
            type_="foreignkey")
    op.create_foreign_key(
            constraint_name="tracker_webhook_subscription_tracker_id_fkey",
            source_table="tracker_webhook_subscription",
            referent_table="tracker",
            local_cols=["tracker_id"],
            remote_cols=["id"],
            ondelete="CASCADE")
    op.drop_constraint(
            constraint_name="ticket_webhook_subscription_ticket_id_fkey",
            table_name="ticket_webhook_subscription",
            type_="foreignkey")
    op.create_foreign_key(
            constraint_name="ticket_webhook_subscription_ticket_id_fkey",
            source_table="ticket_webhook_subscription",
            referent_table="ticket",
            local_cols=["ticket_id"],
            remote_cols=["id"],
            ondelete="CASCADE")
    op.drop_constraint(
            constraint_name="tracker_webhook_delivery_subscription_id_fkey",
            table_name="tracker_webhook_delivery",
            type_="foreignkey")
    op.create_foreign_key(
            constraint_name="tracker_webhook_delivery_subscription_id_fkey",
            source_table="tracker_webhook_delivery",
            referent_table="tracker_webhook_subscription",
            local_cols=["subscription_id"],
            remote_cols=["id"],
            ondelete="CASCADE")
    op.drop_constraint(
            constraint_name="ticket_webhook_delivery_subscription_id_fkey",
            table_name="ticket_webhook_delivery",
            type_="foreignkey")
    op.create_foreign_key(
            constraint_name="ticket_webhook_delivery_subscription_id_fkey",
            source_table="ticket_webhook_delivery",
            referent_table="ticket_webhook_subscription",
            local_cols=["subscription_id"],
            remote_cols=["id"],
            ondelete="CASCADE")


def downgrade():
    op.drop_constraint(
            constraint_name="tracker_webhook_subscription_tracker_id_fkey",
            table_name="tracker_webhook_subscription",
            type_="foreignkey")
    op.create_foreign_key(
            constraint_name="tracker_webhook_subscription_tracker_id_fkey",
            source_table="tracker_webhook_subscription",
            referent_table="tracker",
            local_cols=["tracker_id"],
            remote_cols=["id"])
    op.drop_constraint(
            constraint_name="ticket_webhook_subscription_ticket_id_fkey",
            table_name="ticket_webhook_subscription",
            type_="foreignkey")
    op.create_foreign_key(
            constraint_name="ticket_webhook_subscription_ticket_id_fkey",
            source_table="ticket_webhook_subscription",
            referent_table="ticket",
            local_cols=["ticket_id"],
            remote_cols=["id"])
    op.drop_constraint(
            constraint_name="tracker_webhook_delivery_subscription_id_fkey",
            table_name="tracker_webhook_delivery",
            type_="foreignkey")
    op.create_foreign_key(
            constraint_name="tracker_webhook_delivery_subscription_id_fkey",
            source_table="tracker_webhook_delivery",
            referent_table="tracker_webhook_subscription",
            local_cols=["subscription_id"],
            remote_cols=["id"])
    op.drop_constraint(
            constraint_name="ticket_webhook_delivery_subscription_id_fkey",
            table_name="ticket_webhook_delivery",
            type_="foreignkey")
    op.create_foreign_key(
            constraint_name="ticket_webhook_delivery_subscription_id_fkey",
            source_table="ticket_webhook_delivery",
            referent_table="ticket_webhook_subscription",
            local_cols=["subscription_id"],
            remote_cols=["id"])
