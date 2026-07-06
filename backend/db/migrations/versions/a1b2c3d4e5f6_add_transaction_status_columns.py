"""Add transaction_status and is_deferred_release_event to sp_transactions.

transaction_status mirrors raw_json->>'transactionStatus' for fast filtering.

is_deferred_release_event is TRUE for RELEASED Shipment transactions that have a
DEFERRED_TRANSACTION_ID in their relatedIdentifiers. These represent the monetary
release event for a previously-deferred order; the original order is already counted
via the corresponding DEFERRED_RELEASED transaction (at the shipment date). Including
both would double-count that order in the P&L.

Revision ID: a1b2c3d4e5f6
Revises: feccfae1778b
Create Date: 2026-07-06
"""

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str = "feccfae1778b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE sp_transactions
            ADD COLUMN IF NOT EXISTS transaction_status text,
            ADD COLUMN IF NOT EXISTS is_deferred_release_event boolean NOT NULL DEFAULT false;

        -- Backfill from raw_json
        UPDATE sp_transactions
        SET transaction_status = raw_json->>'transactionStatus';

        -- Mark release events: RELEASED Shipments that have DEFERRED_TRANSACTION_ID
        UPDATE sp_transactions
        SET is_deferred_release_event = true
        WHERE raw_json->>'transactionStatus' = 'RELEASED'
          AND raw_json->'relatedIdentifiers' @> '[{"relatedIdentifierName": "DEFERRED_TRANSACTION_ID"}]';

        CREATE INDEX IF NOT EXISTS ix_sp_transactions_status
            ON sp_transactions (transaction_status);
        CREATE INDEX IF NOT EXISTS ix_sp_transactions_release_event
            ON sp_transactions (is_deferred_release_event)
            WHERE is_deferred_release_event = true;
    """)


def downgrade() -> None:
    op.execute("""
        DROP INDEX IF EXISTS ix_sp_transactions_release_event;
        DROP INDEX IF EXISTS ix_sp_transactions_status;
        ALTER TABLE sp_transactions
            DROP COLUMN IF EXISTS is_deferred_release_event,
            DROP COLUMN IF EXISTS transaction_status;
    """)
