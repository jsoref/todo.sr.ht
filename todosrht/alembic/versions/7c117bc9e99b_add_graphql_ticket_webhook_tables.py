"""Add GraphQL ticket webhook tables

Revision ID: 7c117bc9e99b
Revises: 87daab81985b
Create Date: 2022-04-27 09:16:21.180937

"""

# revision identifiers, used by Alembic.
revision = '7c117bc9e99b'
down_revision = '87daab81985b'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.execute("""
    CREATE TYPE ticket_webhook_event AS ENUM (
        'TICKET_UPDATE',
        'EVENT_CREATED'
    );

    CREATE TABLE gql_ticket_wh_sub (
        id serial PRIMARY KEY,
        created timestamp NOT NULL,
        events ticket_webhook_event[] NOT NULL check (array_length(events, 1) > 0),
        url varchar NOT NULL,
        query varchar NOT NULL,

        auth_method auth_method NOT NULL check (auth_method in ('OAUTH2', 'INTERNAL')),
        token_hash varchar(128) check ((auth_method = 'OAUTH2') = (token_hash IS NOT NULL)),
        grants varchar,
        client_id uuid,
        expires timestamp check ((auth_method = 'OAUTH2') = (expires IS NOT NULL)),
        node_id varchar check ((auth_method = 'INTERNAL') = (node_id IS NOT NULL)),

        user_id integer NOT NULL references "user"(id),
        tracker_id integer NOT NULL references "tracker"(id) ON DELETE CASCADE,
        ticket_id integer NOT NULL references "ticket"(id) ON DELETE CASCADE,
        scoped_id integer NOT NULL
    );

    CREATE INDEX gql_ticket_wh_sub_token_hash_idx ON gql_ticket_wh_sub (token_hash);

    CREATE TABLE gql_ticket_wh_delivery (
        id serial PRIMARY KEY,
        uuid uuid NOT NULL,
        date timestamp NOT NULL,
        event ticket_webhook_event NOT NULL,
        subscription_id integer NOT NULL references gql_ticket_wh_sub(id) ON DELETE CASCADE,
        request_body varchar NOT NULL,
        response_body varchar,
        response_headers varchar,
        response_status integer
    );
    """)


def downgrade():
    op.execute("""
    DROP TABLE gql_ticket_wh_delivery;
    DROP INDEX gql_ticket_wh_sub_token_hash_idx;
    DROP TABLE gql_ticket_wh_sub;
    DROP TYPE ticket_webhook_event;
    """)
