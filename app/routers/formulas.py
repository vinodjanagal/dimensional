from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.auth import get_current_user
from app.core.database import get_db
from app.models import User
from app.schemas.formula import FormulaCreate, FormulaResponse
from app.services import formula_service
from app.services.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)


router = APIRouter(prefix="/notes/{note_id}/formulas", tags=["Formulas"])


@router.get("", response_model=list[FormulaResponse])
async def list_formulas(
    note_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await formula_service.list_formulas(db, note_id, current_user)
    except NotFoundError as e:
        raise _as_http(e, 404)


@router.post(
    "",
    response_model=FormulaResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_formula(
    note_id: int,
    payload: FormulaCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await formula_service.create_formula(
            db=db,
            note_id=note_id,
            user=current_user,
            name=payload.name,
            expression=payload.expression,
            result_unit_symbol=payload.result_unit_symbol,
        )
    except NotFoundError as e:
        raise _as_http(e, 404)
    except ConflictError as e:
        raise _as_http(e, 409)
    except ValidationError as e:
        raise _as_http(e, 422)


def _as_http(exc: Exception, code: int):
    from fastapi import HTTPException
    return HTTPException(status_code=code, detail=str(exc))