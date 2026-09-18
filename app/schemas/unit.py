from decimal import Decimal

from pydantic import BaseModel, Field


class UnitResponse(BaseModel):
    id: int
    name: str
    symbol: str
    dimension: list[int]
    factor: Decimal
    offset: Decimal
    is_base: bool

    model_config = {"from_attributes": True}


class ConversionRequest(BaseModel):
    value: Decimal = Field(
        ...,
        description="The numeric value to convert",
        examples=["5", "273.15"],
    )
    from_symbol: str = Field(..., examples=["km"])
    to_symbol: str = Field(..., examples=["m"])


class ConversionResponse(BaseModel):
    value: Decimal = Field(..., description="Converted numeric value")
    unit: str = Field(..., description="Target unit symbol")
    input_value: Decimal
    input_unit: str


class CompatibilityRequest(BaseModel):
    a: str = Field(..., examples=["km"])
    b: str = Field(..., examples=["m"])


class CompatibilityResponse(BaseModel):
    compatible: bool
    a_dimension: list[int]
    b_dimension: list[int]