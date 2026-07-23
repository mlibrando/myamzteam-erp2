"""Daily-grain P&L for custom date ranges — a date-keyed mirror of pnl_monthly.

Same classification/attribution/COGS as the monthly build (sync.aggregate + sync.cogs),
keyed on the full attribution date instead of the month. Populated by sync.aggregate_daily.
Invariant (guarded): Σ pnl_daily over each month == pnl_monthly. Additive — pnl_monthly and the
reconcile/drift guards are untouched.

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-07-23
"""

from alembic import op

revision: str = "b8c9d0e1f2a3"
down_revision: str = "a7b8c9d0e1f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS pnl_daily (
            marketplace_id text          NOT NULL,
            date           date          NOT NULL,
            line_key       text          NOT NULL,
            line_label     text          NOT NULL,
            bucket         text          NOT NULL,
            amount         numeric(18,4) NOT NULL,
            currency       text          NOT NULL,
            computed_at    timestamptz   NOT NULL DEFAULT now(),
            PRIMARY KEY (marketplace_id, date, bucket, line_key)
        );
        CREATE INDEX IF NOT EXISTS ix_pnl_daily_mp_date
            ON pnl_daily (marketplace_id, date);
    """)


def downgrade() -> None:
    op.execute("""
        DROP INDEX IF EXISTS ix_pnl_daily_mp_date;
        DROP TABLE IF EXISTS pnl_daily;
    """)
