from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Note as NoteModel
from app.schemas import NoteResponse, NoteCreate

from app.services.note_service import (
    get_note,
    get_notes as get_notes_service,
    create_note as create_note_service,
    update_note as update_note_service,
    delete_note as delete_note_service,
)

from app.auth.auth import get_current_user


router = APIRouter(prefix="/notes", tags=["Notes"])


@router.get("", response_model=list[NoteResponse])
async def get_notes(
    db: AsyncSession = Depends(get_db),
    current_user= Depends(get_current_user)
    ):

    return await get_notes_service(db,current_user.id)


@router.post("", response_model=NoteResponse)
async def create_note(
    note: NoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user= Depends(get_current_user),
):

    return await create_note_service(
        db, 
        note.title,
        note.content,
        current_user.id
    )


@router.get("/{note_id}", response_model=NoteResponse)
async def get_note_by_id(
    note_id:int,
    db: AsyncSession = Depends(get_db), 
    current_user = Depends(get_current_user),
):


    note = await get_note(db, note_id, current_user.id)

    if note is None:
        raise HTTPException(
            status_code=404,
            detail="Note not found",
        )

    return note


@router.put("/{note_id}", response_model=NoteResponse)
async def update_note(
    note_id: int,
    note_data: NoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    note = await update_note_service(
        db, 
        note_id,
        note_data.title,
        note_data.content,
        current_user.id,
    )

    if note is None:
        raise HTTPException(
            status_code=404,
            detail="Note not found",
        )

    return note


@router.delete("/{note_id}")
async def delete_note(note_id: int, db: AsyncSession = Depends(get_db), current_user = Depends(get_current_user)):
    note = await delete_note_service(
        db, note_id, current_user.id
    )

    if note is None:
        raise HTTPException(
            status_code=404,
            detail="Note not found",
        )

    return {"message": "Note deleted successfully"}