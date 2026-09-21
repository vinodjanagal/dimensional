from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.types import DecimalStr
from app.schemas.unit import UnitResponse


class QuantityCreate(BaseModel):
    value: DecimalStr = Field(..., examples=["9.81", "3.14"])
    unit_symbol: str = Field(..., examples=["m", "kg", "s"])
    uncertainty: DecimalStr | None = Field(default=None, examples=["0.01"])


class QuantityResponse(BaseModel):
    id: int
    note_id: int
    value: DecimalStr
    uncertainty: DecimalStr | None
    unit: UnitResponse
    created_at: datetime

    model_config = {"from_attributes": True}