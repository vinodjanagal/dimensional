from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.unit import Unit

class Formula(Base):
    __tablename__ = "formulas"

    id: Mapped[int] = mapped_column(primary_key=True)

    note_id: Mapped[int] = mapped_column(
        ForeignKey(
            "notes.id",
            ondelete="CASCADE",
            name="fk_formulas_note_id_notes",
        ),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)

    expression: Mapped[str] = mapped_column(Text, nullable=False)

    result_unit_id: Mapped[int] = mapped_column(
        ForeignKey("units.id", name="fk_formulas_result_unit_id_units"),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("note_id", "name", name="uq_formulas_note_id_name"),
    )

    result_unit: Mapped["Unit"] = relationship("Unit", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Formula {self.name} = {self.expression}>"