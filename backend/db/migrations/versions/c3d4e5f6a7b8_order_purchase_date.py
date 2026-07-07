"""Persist AmazonOrderId → PurchaseDate for date-basis re-attribution.

Sellerise attributes revenue by order PurchaseDate (when the customer bought)
while listTransactions gives us postedDate (when the financial event posted).
Re-attributing requires a persisted map fetched via the Orders API.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-07-06
"""

from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: str = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS order_purchase_date (
            order_id       text PRIMARY KEY,
            marketplace_id text        NOT NULL,
            purchase_date  timestamptz NOT NULL,
            last_update    timestamptz,
            order_status   text,
            ingested_at    timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS ix_opd_marketplace_purchase
            ON order_purchase_date (marketplace_id, purchase_date);
    """)


def downgrade() -> None:
    op.execute("""
        DROP INDEX IF EXISTS ix_opd_marketplace_purchase;
        DROP TABLE IF EXISTS order_purchase_date;
    """)
