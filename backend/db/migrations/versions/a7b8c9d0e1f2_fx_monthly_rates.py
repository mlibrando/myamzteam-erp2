"""Monthly-average FX rates (native → USD) for the dashboard's USD view.

One row per (currency, year_month): the average of a daily FX feed's rates for that month,
stored as native→USD (1 unit of `currency` = `rate_to_usd` USD). The dashboard reads this to
convert CA/UK/AU figures to USD; a missing (currency, month) falls back to the fixed book rate.
Populated by `sync.fx_rates` (pull daily → average → upsert), not per-request.

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-07-23
"""

from alembic import op

revision: str = "a7b8c9d0e1f2"
down_revision: str = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS fx_monthly_rates (
            currency    text          NOT NULL,
            year_month  char(7)       NOT NULL,
            rate_to_usd numeric(18,8) NOT NULL,
            source      text          NOT NULL,
            day_count   integer       NOT NULL,
            pulled_at   timestamptz   NOT NULL DEFAULT now(),
            PRIMARY KEY (currency, year_month)
        );
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS fx_monthly_rates;")
