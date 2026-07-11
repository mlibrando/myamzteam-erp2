"""Append-only history of superseded ad_spend_daily rows.

`ad_spend_daily` is replace-in-place: `_replace_month` deletes a (marketplace,
month) and reinserts. That makes `as_of` a pull timestamp but NOT a horizon —
the pre-restatement value is physically gone, so filtering the live table on
`as_of <= H` cannot reconstruct the state at H.

The drift guard's DEFECT_REMEASURED test needs exactly that reconstruction for
AU, whose FX reference rate is anchored on advertising. This table keeps the
superseded rows so the reconstruction is possible: each row records the version
that was live during `[as_of, superseded_at)`.

Additive only — no change to `ad_spend_daily` or any reader.

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-07-10
"""

from alembic import op

revision: str = "f6a7b8c9d0e1"
down_revision: str = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS ad_spend_history (
            marketplace_id      text NOT NULL,
            date                date NOT NULL,
            campaign_id         text NOT NULL,
            ad_product          text NOT NULL,
            campaign_name       text,
            campaign_country    text,
            budget_currency     text,
            total_cost          numeric(18,4) NOT NULL,
            updated_at          timestamptz,
            as_of               timestamptz NOT NULL,
            superseded_at       timestamptz NOT NULL
        );

        -- The reconstruction filters by marketplace + currency and validity
        -- interval, so index the interval bounds.
        CREATE INDEX IF NOT EXISTS ix_ash_marketplace_currency
            ON ad_spend_history (marketplace_id, budget_currency);
        CREATE INDEX IF NOT EXISTS ix_ash_validity
            ON ad_spend_history (as_of, superseded_at);
    """)


def downgrade() -> None:
    op.execute("""
        DROP INDEX IF EXISTS ix_ash_validity;
        DROP INDEX IF EXISTS ix_ash_marketplace_currency;
        DROP TABLE IF EXISTS ad_spend_history;
    """)
