from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories import unit_repository
from app.schemas.unit import (
    CompatibilityRequest,
    CompatibilityResponse,
    ConversionRequest,
    ConversionResponse,
    UnitResponse,
)
from app.services.unit_service import (
    IncompatibleUnitsError,
    convert,
    is_compatible,
)

from app.schemas.unit import ValidateExpressionRequest, ValidateExpressionResponse
from app.services.expression import ExpressionError, evaluate_dimension

router = APIRouter(prefix="/units", tags=["Units"])


@router.get("", response_model=list[UnitResponse])
async def list_units(db: AsyncSession = Depends(get_db)):
    return await unit_repository.list_all(db)


@router.post("/convert", response_model=ConversionResponse)
async def convert_value(
    req: ConversionRequest,
    db: AsyncSession = Depends(get_db),
):
    frm = await unit_repository.get_by_symbol(db, req.from_symbol)
    if frm is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown unit: {req.from_symbol!r}",
        )

    to = await unit_repository.get_by_symbol(db, req.to_symbol)
    if to is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown unit: {req.to_symbol!r}",
        )

    try:
        result = convert(req.value, frm, to)
    except IncompatibleUnitsError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )

    return ConversionResponse(
        value=result,
        unit=to.symbol,
        input_value=req.value,
        input_unit=frm.symbol,
    )


@router.post("/check-compatibility", response_model=CompatibilityResponse)
async def check_compatibility(
    req: CompatibilityRequest,
    db: AsyncSession = Depends(get_db),
):
    a = await unit_repository.get_by_symbol(db, req.a)
    if a is None:
        raise HTTPException(404, f"Unknown unit: {req.a!r}")

    b = await unit_repository.get_by_symbol(db, req.b)
    if b is None:
        raise HTTPException(404, f"Unknown unit: {req.b!r}")

    return CompatibilityResponse(
        compatible=is_compatible(a, b),
        a_dimension=a.dimension,
        b_dimension=b.dimension,
    )

@router.post("/validate-expression", response_model=ValidateExpressionResponse)
async def validate_expression(
    req: ValidateExpressionRequest,
    db: AsyncSession = Depends(get_db),
):
    # Build a lookup over ALL units in the DB
    all_units = await unit_repository.list_all(db)
    lookup = {u.symbol: tuple(u.dimension) for u in all_units}

    expected = await unit_repository.get_by_symbol(db, req.expected_unit)
    if expected is None:
        raise HTTPException(404, f"Unknown expected unit: {req.expected_unit!r}")

    try:
        expr_dim = evaluate_dimension(req.expression, lookup.__getitem__)
    except ExpressionError as e:
        raise HTTPException(422, str(e))

    expected_dim = tuple(expected.dimension)
    valid = expr_dim == expected_dim

    return ValidateExpressionResponse(
        valid=valid,
        expression=req.expression,
        expression_dimension=list(expr_dim),
        expected_unit=req.expected_unit,
        expected_dimension=list(expected_dim),
        message=(
            None
            if valid
            else f"Expression has dimension {list(expr_dim)}, "
                 f"but unit {req.expected_unit!r} has {list(expected_dim)}"
        ),
    )