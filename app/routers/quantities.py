from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.auth import get_current_user
from app.core.database import get_db
from app.models import Note, Quantity, User
from app.repositories import quantity_repository, unit_repository
from app.schemas.quantity import QuantityCreate, QuantityResponse
from app.services.exceptions import NotFoundError


router = APIRouter(prefix="/notes/{note_id}/quantities", tags=["Quantities"])


async def _get_owned_note(
    db: AsyncSession, note_id: int, user: User
) -> Note:
    note = await db.get(Note, note_id)
    if note is None or note.owner_id != user.id:
        raise HTTPException(404, f"Note {note_id} not found")
    return note


@router.get("", response_model=list[QuantityResponse])
async def list_quantities(
    note_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_owned_note(db, note_id, current_user)
    return await quantity_repository.list_for_note(db, note_id)


@router.post("", response_model=QuantityResponse, status_code=status.HTTP_201_CREATED)
async def create_quantity(
    note_id: int,
    payload: QuantityCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_owned_note(db, note_id, current_user)

    unit = await unit_repository.get_by_symbol(db, payload.unit_symbol)
    if unit is None:
        raise HTTPException(404, f"Unknown unit: {payload.unit_symbol!r}")

    q = Quantity(
        note_id=note_id,
        unit_id=unit.id,
        value=payload.value,
        uncertainty=payload.uncertainty,
    )
    q = await quantity_repository.create(db, q)
    await db.commit()
    await db.refresh(q, ["unit"])
    return q