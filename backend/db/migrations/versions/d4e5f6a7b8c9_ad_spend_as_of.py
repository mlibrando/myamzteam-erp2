"""Add as_of and PK to ad_spend_daily.

Amazon Ads reports get restated for a period after generation, so the same
month can return slightly different numbers on different pull dates. Storing an
`as_of` timestamp per row lets us later distinguish restatement drift (expected
sub-dollar month-level change) from a real pipeline change (a bug) — without
the timestamp, they're indistinguishable.

Table was empty at migration time, so we can add the PK unconditionally.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-07-07
"""

from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: str = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        TRUNCATE TABLE ad_spend_daily;

        ALTER TABLE ad_spend_daily
            ADD COLUMN IF NOT EXISTS as_of timestamptz NOT NULL DEFAULT now();

        ALTER TABLE ad_spend_daily DROP CONSTRAINT IF EXISTS ad_spend_daily_pkey;

        ALTER TABLE ad_spend_daily
            ADD CONSTRAINT ad_spend_daily_pkey
            PRIMARY KEY (marketplace_id, date, campaign_id, ad_product);

        CREATE INDEX IF NOT EXISTS ix_asd_marketplace_date
            ON ad_spend_daily (marketplace_id, date);
    """)


def downgrade() -> None:
    op.execute("""
        DROP INDEX IF EXISTS ix_asd_marketplace_date;
        ALTER TABLE ad_spend_daily DROP CONSTRAINT IF EXISTS ad_spend_daily_pkey;
        ALTER TABLE ad_spend_daily DROP COLUMN IF EXISTS as_of;
    """)
