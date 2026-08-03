import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class InvestmentCategory(str, enum.Enum):
    FIXED_INCOME = "fixed_income"
    EQUITY = "equity"
    PRECIOUS_METAL = "precious_metal"
    PHYSICAL = "physical"
    OTHER = "other"


class ValuationMethod(str, enum.Enum):
    MANUAL = "manual"
    NAV = "nav"
    SPOT_RATE = "spot_rate"
    FORMULA_ACCRUAL = "formula_accrual"
    MARKET_PRICE = "market_price"


class InvestmentStatus(str, enum.Enum):
    ACTIVE = "active"
    MATURED = "matured"
    SOLD = "sold"


class InvestmentTxnType(str, enum.Enum):
    BUY = "buy"
    SELL = "sell"
    INTEREST_CREDIT = "interest_credit"
    MATURITY = "maturity"
    REDEMPTION = "redemption"


class InvestmentType(Base):
    __tablename__ = "investment_types"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[InvestmentCategory] = mapped_column(
        Enum(InvestmentCategory, name="investment_category", native_enum=False, length=32, values_callable=lambda x: [e.value for e in x]), nullable=False
    )
    valuation_method: Mapped[ValuationMethod] = mapped_column(
        Enum(ValuationMethod, name="valuation_method", native_enum=False, length=32, values_callable=lambda x: [e.value for e in x]), nullable=False
    )
    # field_schema is the ONE source of truth for what fields an Investment of this type has.
    # Shape: list[{key, label, data_type, required, options?}]
    # data_type in: text | number | date | percent | enum
    field_schema: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


# NOTE: invested_amount and current_value live on the table (not inside attributes) for every
# valuation_method. current_value is denormalized by the valuation job on write so reads are fast.
class Investment(Base):
    __tablename__ = "investments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    investment_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("investment_types.id", ondelete="RESTRICT"), nullable=False
    )
    account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True
    )
    nickname: Mapped[str] = mapped_column(String(255), nullable=False)
    attributes: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    invested_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    current_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="INR")
    status: Mapped[InvestmentStatus] = mapped_column(
        Enum(InvestmentStatus, name="investment_status", native_enum=False, length=16, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=InvestmentStatus.ACTIVE,
    )
    recurring_contribution: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class InvestmentTransaction(Base):
    __tablename__ = "investment_transactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    investment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("investments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    txn_type: Mapped[InvestmentTxnType] = mapped_column(
        Enum(InvestmentTxnType, name="investment_txn_type", native_enum=False, length=32, values_callable=lambda x: [e.value for e in x]), nullable=False
    )
    units: Mapped[Decimal | None] = mapped_column(Numeric(24, 6), nullable=True)
    price_per_unit: Mapped[Decimal | None] = mapped_column(Numeric(24, 6), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)


class InvestmentValuation(Base):
    __tablename__ = "investment_valuations"
    __table_args__ = (UniqueConstraint("investment_id", "date", name="uq_valuation_inv_date"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    investment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("investments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    value_per_unit: Mapped[Decimal | None] = mapped_column(Numeric(24, 6), nullable=True)
    total_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
