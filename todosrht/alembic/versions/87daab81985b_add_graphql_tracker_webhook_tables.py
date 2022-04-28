"""Add GraphQL tracker webhook tables

Revision ID: 87daab81985b
Revises: dbed5c6ea613
Create Date: 2022-04-11 14:21:35.885142

"""

# revision identifiers, used by Alembic.
revision = '87daab81985b'
down_revision = 'dbed5c6ea613'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.execute("""
    CREATE TYPE tracker_webhook_event AS ENUM (
        'TRACKER_UPDATE',
        'TRACKER_DELETED',
        'TICKET_CREATED',
        'TICKET_UPDATE',
        'LABEL_CREATED',
        'LABEL_UPDATE',
        'LABEL_DELETED',
        'EVENT_CREATED'
    );

    CREATE TABLE gql_tracker_wh_sub (
        id serial PRIMARY KEY,
        created timestamp NOT NULL,
        events tracker_webhook_event[] NOT NULL check (array_length(events, 1) > 0),
        url varchar NOT NULL,
        query varchar NOT NULL,

        auth_method auth_method NOT NULL check (auth_method in ('OAUTH2', 'INTERNAL')),
        token_hash varchar(128) check ((auth_method = 'OAUTH2') = (token_hash IS NOT NULL)),
        grants varchar,
        client_id uuid,
        expires timestamp check ((auth_method = 'OAUTH2') = (expires IS NOT NULL)),
        node_id varchar check ((auth_method = 'INTERNAL') = (node_id IS NOT NULL)),

        user_id integer NOT NULL references "user"(id),
        tracker_id integer NOT NULL references "tracker"(id) ON DELETE CASCADE
    );

    CREATE INDEX gql_tracker_wh_sub_token_hash_idx ON gql_tracker_wh_sub (token_hash);

    CREATE TABLE gql_tracker_wh_delivery (
        id serial PRIMARY KEY,
        uuid uuid NOT NULL,
        date timestamp NOT NULL,
        event tracker_webhook_event NOT NULL,
        subscription_id integer NOT NULL references gql_tracker_wh_sub(id) ON DELETE CASCADE,
        request_body varchar NOT NULL,
        response_body varchar,
        response_headers varchar,
        response_status integer
    );
    """)


def downgrade():
    op.execute("""
    DROP TABLE gql_tracker_wh_delivery;
    DROP INDEX gql_tracker_wh_sub_token_hash_idx;
    DROP TABLE gql_tracker_wh_sub;
    DROP TYPE tracker_webhook_event;
    """)
