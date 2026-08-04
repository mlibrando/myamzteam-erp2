"""Company-wide salary overrides for the ALL-view contribution rows.

One row per month: the daily salary (USD) that overrides the code-level default schedule
(pnl._default_daily_salary). The dashboard's ALL view reads this to compute the Salaries
Daily / Contribution rows; a missing month falls back to the built-in default. Written by
the dashboard's gear/dialog editor via PUT /salaries — global (no marketplace_id), since
payroll is a single company cost surfaced only on the ALL tab.

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-08-04
"""

from alembic import op

revision: str = "c9d0e1f2a3b4"
down_revision: str = "b8c9d0e1f2a3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS salary_override (
            year_month   char(7)       NOT NULL,
            daily_amount numeric(18,4) NOT NULL,
            updated_at   timestamptz   NOT NULL DEFAULT now(),
            PRIMARY KEY (year_month)
        );
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS salary_override;")
