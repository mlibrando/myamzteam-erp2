"""initial schema

Revision ID: feccfae1778b
Revises:
Create Date: 2026-07-05 23:18:16.881728

Creates the 11 core tables for the P&L ERP: sp_transactions + child tables,
sales_daily, ads_reports, ad_spend_daily, cogs_per_sku, cogs_missing_skus,
sync_state, unmapped_breakdown_types, pnl_monthly.

Uses raw SQL via op.execute — we do not use SQLAlchemy ORM, so autogenerate is
disabled and every future migration is hand-written.
"""

from typing import Sequence, Union

from alembic import op


revision: str = "feccfae1778b"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


DDL_UPGRADE = """
CREATE TABLE IF NOT EXISTS sp_transactions (
    transaction_id    text PRIMARY KEY,
    marketplace_id    text NOT NULL,
    posted_at         timestamptz NOT NULL,
    total_amount      numeric(18,4),
    currency          text,
    raw_json          jsonb NOT NULL,
    ingested_at       timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_sp_transactions_marketplace_posted
    ON sp_transactions (marketplace_id, posted_at);

CREATE TABLE IF NOT EXISTS sp_breakdowns (
    id                bigserial PRIMARY KEY,
    transaction_id    text NOT NULL REFERENCES sp_transactions(transaction_id) ON DELETE CASCADE,
    breakdown_type    text NOT NULL,
    breakdown_amount  numeric(18,4) NOT NULL,
    currency          text
);
CREATE INDEX IF NOT EXISTS ix_sp_breakdowns_txn ON sp_breakdowns (transaction_id);
CREATE INDEX IF NOT EXISTS ix_sp_breakdowns_type ON sp_breakdowns (breakdown_type);

CREATE TABLE IF NOT EXISTS sp_transaction_items (
    id                bigserial PRIMARY KEY,
    transaction_id    text NOT NULL REFERENCES sp_transactions(transaction_id) ON DELETE CASCADE,
    sku               text,
    asin              text,
    quantity_shipped  integer
);
CREATE INDEX IF NOT EXISTS ix_sp_txn_items_txn ON sp_transaction_items (transaction_id);
CREATE INDEX IF NOT EXISTS ix_sp_txn_items_sku ON sp_transaction_items (sku);

CREATE TABLE IF NOT EXISTS sales_daily (
    marketplace_id       text NOT NULL,
    date                 date NOT NULL,
    unit_count           integer,
    order_item_count     integer,
    total_sales          numeric(18,4),
    average_unit_price   numeric(18,4),
    currency             text,
    updated_at           timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (marketplace_id, date)
);

CREATE TABLE IF NOT EXISTS ads_reports (
    id                 bigserial PRIMARY KEY,
    marketplace_id     text NOT NULL,
    period_start       date NOT NULL,
    period_end         date NOT NULL,
    amazon_report_id   text UNIQUE,
    status             text NOT NULL,
    created_at         timestamptz NOT NULL DEFAULT now(),
    completed_at       timestamptz,
    failure_code       text,
    failure_reason     text
);
CREATE INDEX IF NOT EXISTS ix_ads_reports_status ON ads_reports (status);

CREATE TABLE IF NOT EXISTS ad_spend_daily (
    marketplace_id      text NOT NULL,
    date                date NOT NULL,
    campaign_id         text NOT NULL,
    ad_product          text NOT NULL,
    campaign_name       text,
    campaign_country    text,
    budget_currency     text,
    total_cost          numeric(18,4) NOT NULL,
    updated_at          timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (marketplace_id, date, campaign_id, ad_product)
);

CREATE TABLE IF NOT EXISTS cogs_per_sku (
    marketplace_id     text NOT NULL,
    sku                text NOT NULL,
    asin               text,
    product_name       text,
    status             text,
    normal_price       numeric(18,4),
    cogs               numeric(18,4) NOT NULL,
    imported_at        timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (marketplace_id, sku)
);

CREATE TABLE IF NOT EXISTS cogs_missing_skus (
    marketplace_id     text NOT NULL,
    sku                text NOT NULL,
    asin               text,
    first_seen         timestamptz NOT NULL DEFAULT now(),
    last_seen          timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (marketplace_id, sku)
);

CREATE TABLE IF NOT EXISTS sync_state (
    key                text PRIMARY KEY,
    last_posted_at     timestamptz,
    next_token         text,
    updated_at         timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS unmapped_breakdown_types (
    breakdown_type         text PRIMARY KEY,
    first_seen             timestamptz NOT NULL DEFAULT now(),
    last_seen              timestamptz NOT NULL DEFAULT now(),
    occurrences            bigint NOT NULL DEFAULT 0,
    sample_transaction_id  text
);

CREATE TABLE IF NOT EXISTS pnl_monthly (
    marketplace_id     text NOT NULL,
    year_month         char(7) NOT NULL,
    line_key           text NOT NULL,
    line_label         text NOT NULL,
    bucket             text NOT NULL,
    amount             numeric(18,4) NOT NULL,
    currency           text NOT NULL,
    computed_at        timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (marketplace_id, year_month, line_key)
);
"""

DDL_DOWNGRADE = """
DROP TABLE IF EXISTS pnl_monthly;
DROP TABLE IF EXISTS unmapped_breakdown_types;
DROP TABLE IF EXISTS sync_state;
DROP TABLE IF EXISTS cogs_missing_skus;
DROP TABLE IF EXISTS cogs_per_sku;
DROP TABLE IF EXISTS ad_spend_daily;
DROP TABLE IF EXISTS ads_reports;
DROP TABLE IF EXISTS sales_daily;
DROP TABLE IF EXISTS sp_transaction_items;
DROP TABLE IF EXISTS sp_breakdowns;
DROP TABLE IF EXISTS sp_transactions;
"""


def upgrade() -> None:
    op.execute(DDL_UPGRADE)


def downgrade() -> None:
    op.execute(DDL_DOWNGRADE)
