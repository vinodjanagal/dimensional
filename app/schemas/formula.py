from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.unit import UnitResponse


class FormulaCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, examples=["kinetic_energy"])
    expression: str = Field(
        ...,
        min_length=1,
        examples=["0.5 * m * v ** 2", "m * g * h"],
    )
    result_unit_symbol: str = Field(..., examples=["J", "N", "m"])


class FormulaResponse(BaseModel):
    id: int
    note_id: int
    name: str
    expression: str
    result_unit: UnitResponse
    created_at: datetime

    model_config = {"from_attributes": True}