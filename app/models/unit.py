from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Unit(Base):
    __tablename__ = "units"

    id: Mapped[int] = mapped_column(primary_key= True)

    name: Mapped[str] = mapped_column(
        String(100),
        nullable= False,
    )

    symbol: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        index=True,
        nullable= False,
    )

    # 7- tuple of integer exponents for (M, L, T, I, Θ, N, J)

    dimension: Mapped[list[int]] = mapped_column(
        JSONB,
        nullable= False,
    )

    # Multiplier to convert to the SI base unit of this dimension
    factor: Mapped[Decimal] = mapped_column(
        Numeric(38, 20),
        nullable = False,
        default= Decimal("1"),
    ) 

    # Additive offset (for temperature scales: 0 C = 273.15 K)

    offset: Mapped[Decimal]= mapped_column(
        Numeric(38, 20),
        nullable= False,
        default= Decimal("0"),
    )

    # True for the 7 SI base units; False for every derived or prefixed unit
    is_base: Mapped[bool] =mapped_column(
        Boolean,
        nullable= False,
        default= False,
    )

    # Points at the base unit of this dimension. NULL for the 7 SI base units.
    base_unit_id: Mapped[int | None] = mapped_column(
        ForeignKey("units.id", name="fk_units_base_unit_id_units"),
        nullable=True,
    )

    base_unit: Mapped["Unit | None"] = relationship(
        "Unit",
        remote_side="Unit.id",
        backref="derived_units",
    )

    def __repr__(self) -> str:
        return f"<Unit {self.symbol} dim={self.dimension}>"