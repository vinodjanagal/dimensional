
from app.models import Note as NoteModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import Session


async def get_note(db: AsyncSession, note_id: int, user_id: int):
    result = await db.execute(
        select(NoteModel)
        .where(
            NoteModel.id == note_id,
            NoteModel.owner_id == user_id,
        )
    )

    return result.scalar_one_or_none()


async def get_notes(db: AsyncSession, user_id: int):
    result = await db.execute(
         select(NoteModel)
        .where(NoteModel.owner_id == user_id)
    )

    return result.scalars().all()

async def create_note(db: AsyncSession, note: NoteModel):
    db.add(note)

    await db.flush()
    await db.refresh(note)

    return note

async def update_note(db: AsyncSession, note_id: int, title: str, content: str, user_id: int):

    result = await db.execute(
        select(NoteModel).where(
            NoteModel.id == note_id,
            NoteModel.owner_id == user_id,
        )
    )

    note = result.scalar_one_or_none()

    if note is None:
        return None

    note.title = title
    note.content = content

    return note

async def delete_note(db: AsyncSession, note_id: int, user_id: int):
    result = await db.execute(
        select(NoteModel).where(
            NoteModel.id == note_id,
            NoteModel.owner_id == user_id,
        )
    )

    note = result.scalar_one_or_none()

    if note is None:
        return None

    await db.delete(note)

    return note
