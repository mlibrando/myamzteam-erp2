"""Append-only pnl_monthly snapshots for the vs-prior-pull drift guard.

Every reconcile run writes a full per-(month, bucket, sub_line) snapshot keyed
by `pull_at`. That history is what the DRIFT_VS_PRIOR_PULL guard compares the
current pull's numbers against — a delta-vs-yesterday check rather than only a
delta-vs-Sellerise check.

Append-only by design. Losing the history defeats the guard.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-07-07
"""

from alembic import op

revision: str = "e5f6a7b8c9d0"
down_revision: str = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS pnl_monthly_snapshots (
            pull_at        timestamptz NOT NULL,
            marketplace_id text        NOT NULL,
            year_month     char(7)     NOT NULL,
            bucket         text        NOT NULL,
            sub_line       text        NOT NULL,
            amount         numeric(18,4) NOT NULL,
            PRIMARY KEY (pull_at, marketplace_id, year_month, bucket, sub_line)
        );
        CREATE INDEX IF NOT EXISTS ix_pms_marketplace_ym_bucket
            ON pnl_monthly_snapshots (marketplace_id, year_month, bucket, sub_line, pull_at DESC);
    """)


def downgrade() -> None:
    op.execute("""
        DROP INDEX IF EXISTS ix_pms_marketplace_ym_bucket;
        DROP TABLE IF EXISTS pnl_monthly_snapshots;
    """)
