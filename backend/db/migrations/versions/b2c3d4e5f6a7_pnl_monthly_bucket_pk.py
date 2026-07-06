"""Include bucket in pnl_monthly's primary key.

Sellerise's schema legitimately reuses sub-line names across buckets — e.g.
`feesObject.Commission` and `refundsObject.Commission` are distinct lines with
the same name. The old PK (marketplace_id, year_month, line_key) collided as
soon as the aggregator was rewritten to Sellerise-shaped rows.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-07-06
"""

from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: str = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE pnl_monthly DROP CONSTRAINT IF EXISTS pnl_monthly_pkey;
        ALTER TABLE pnl_monthly
            ADD CONSTRAINT pnl_monthly_pkey
            PRIMARY KEY (marketplace_id, year_month, bucket, line_key);
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE pnl_monthly DROP CONSTRAINT IF EXISTS pnl_monthly_pkey;
        ALTER TABLE pnl_monthly
            ADD CONSTRAINT pnl_monthly_pkey
            PRIMARY KEY (marketplace_id, year_month, line_key);
    """)
