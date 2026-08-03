"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-02
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("auth_provider_id", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_auth_provider_id", "users", ["auth_provider_id"], unique=True)

    op.create_table(
        "institutions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("logo_url", sa.String(500), nullable=True),
    )

    op.create_table(
        "accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("institution_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("institutions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("current_balance", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(8), nullable=False, server_default="INR"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint(
            "type IN ('checking','savings','credit','brokerage','retirement','loan','property')",
            name="ck_accounts_type",
        ),
    )
    op.create_index("ix_accounts_user_id", "accounts", ["user_id"])

    op.create_table(
        "categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("categories.id", ondelete="SET NULL"), nullable=True),
        sa.Column("icon", sa.String(64), nullable=True),
        sa.Column("is_system", sa.Boolean, nullable=False, server_default=sa.false()),
    )

    op.create_table(
        "categorization_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("match_pattern", sa.Text, nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("categories.id", ondelete="CASCADE"), nullable=False),
    )
    op.create_index("ix_categorization_rules_user_id", "categorization_rules", ["user_id"])

    op.create_table(
        "transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("account_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("merchant_raw", sa.String(500), nullable=False),
        sa.Column("merchant_clean", sa.String(500), nullable=True),
        sa.Column("category_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("categories.id", ondelete="SET NULL"), nullable=True),
        sa.Column("is_recurring", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("source", sa.String(16), nullable=False, server_default="manual"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("source IN ('manual','csv','plaid')", name="ck_transactions_source"),
    )
    op.create_index("ix_transactions_account_id", "transactions", ["account_id"])
    op.create_index("ix_transactions_date", "transactions", ["date"])

    op.create_table(
        "budgets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("categories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("month", sa.Date, nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("rollover_enabled", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.UniqueConstraint("user_id", "category_id", "month", name="uq_budget_user_cat_month"),
    )
    op.create_index("ix_budgets_user_id", "budgets", ["user_id"])

    op.create_table(
        "net_worth_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("total_assets", sa.Numeric(18, 2), nullable=False),
        sa.Column("total_liabilities", sa.Numeric(18, 2), nullable=False),
        sa.UniqueConstraint("user_id", "date", name="uq_nw_user_date"),
    )
    op.create_index("ix_net_worth_snapshots_user_id", "net_worth_snapshots", ["user_id"])

    op.create_table(
        "investment_types",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("key", sa.String(120), nullable=False, unique=True),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("valuation_method", sa.String(32), nullable=False),
        sa.Column("field_schema", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("is_system", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.CheckConstraint(
            "category IN ('fixed_income','equity','precious_metal','physical','other')",
            name="ck_it_category",
        ),
        sa.CheckConstraint(
            "valuation_method IN ('manual','nav','spot_rate','formula_accrual','market_price')",
            name="ck_it_valuation",
        ),
    )

    op.create_table(
        "investments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("investment_type_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("investment_types.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("nickname", sa.String(255), nullable=False),
        sa.Column("attributes", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("invested_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("current_value", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(8), nullable=False, server_default="INR"),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("recurring_contribution", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('active','matured','sold')", name="ck_inv_status"),
    )
    op.create_index("ix_investments_user_id", "investments", ["user_id"])

    op.create_table(
        "investment_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("investment_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("investments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("txn_type", sa.String(32), nullable=False),
        sa.Column("units", sa.Numeric(24, 6), nullable=True),
        sa.Column("price_per_unit", sa.Numeric(24, 6), nullable=True),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.CheckConstraint(
            "txn_type IN ('buy','sell','interest_credit','maturity','redemption')",
            name="ck_invtxn_type",
        ),
    )
    op.create_index("ix_investment_transactions_investment_id", "investment_transactions", ["investment_id"])

    op.create_table(
        "investment_valuations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("investment_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("investments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("value_per_unit", sa.Numeric(24, 6), nullable=True),
        sa.Column("total_value", sa.Numeric(18, 2), nullable=False),
        sa.UniqueConstraint("investment_id", "date", name="uq_valuation_inv_date"),
    )
    op.create_index("ix_investment_valuations_investment_id", "investment_valuations", ["investment_id"])


def downgrade() -> None:
    for t in [
        "investment_valuations", "investment_transactions", "investments", "investment_types",
        "net_worth_snapshots", "budgets", "transactions", "categorization_rules", "categories",
        "accounts", "institutions", "users",
    ]:
        op.drop_table(t)
