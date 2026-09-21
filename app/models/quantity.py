from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

from app.models.unit import Unit


class Quantity(Base):
    __tablename__ = "quantities"

    id: Mapped[int] = mapped_column(primary_key=True)

    note_id: Mapped[int] = mapped_column(
        ForeignKey(
            "notes.id",
            ondelete="CASCADE",
            name="fk_quantities_note_id_notes",
        ),
        nullable=False,
        index=True,
    )

    unit_id: Mapped[int] = mapped_column(
        ForeignKey("units.id", name="fk_quantities_unit_id_units"),
        nullable=False,
    )

    value: Mapped[Decimal] = mapped_column(
        Numeric(38, 20),
        nullable=False,
    )

    # Populated in Session 5. Nullable for now.
    uncertainty: Mapped[Decimal | None] = mapped_column(
        Numeric(38, 20),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # cspell:ignore selectin
    unit: Mapped["Unit"] = relationship("Unit", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Quantity {self.value} unit_id={self.unit_id}>"