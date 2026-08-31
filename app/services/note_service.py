from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories import note_repository
from app.models import Note as NoteModel,User


async def get_note(db: AsyncSession, note_id: int, user_id: int):
    return await note_repository.get_note(db, note_id, user_id)


async def get_notes(db: AsyncSession, user_id: int):
    return await note_repository.get_notes(db, user_id)


async def create_note(db: AsyncSession, title:str, content:str, user_id: int):

    note = NoteModel(
        title=title,
        content=content,
        owner_id=user_id,
    )

    try:
        note = await note_repository.create_note(db, note)
        await db.commit()
        return note

    except Exception:
        await db.rollback()
        raise
        

async def update_note(
    db: AsyncSession,
    note_id: int,
    title: str,
    content: str,
    user_id: int,
):

    try:
        note = await note_repository.update_note(
            db,
            note_id,
            title,
            content,
            user_id,
            )
        if note is None:
            return None
        
        await db.commit()
        await db.refresh(note)

        return note

    except Exception:
        await db.rollback()
        raise


async def delete_note(db:AsyncSession, note_id: int, user_id: int):

    try:
        note = await note_repository.delete_note(
        db, 
        note_id, 
        user_id,
    )

        if note is None:
            return None

        await db.commit()
        return note
    
    except Exception:
        await db.rollback()
        raise
