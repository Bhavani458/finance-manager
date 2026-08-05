"""ai news cache

Revision ID: 0002_ai_news_cache
Revises: 0001_initial
Create Date: 2026-08-03
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002_ai_news_cache"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_news_cache",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ai_news_cache_user_id", "ai_news_cache", ["user_id"])


def downgrade() -> None:
    op.drop_table("ai_news_cache")
