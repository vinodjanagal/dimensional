from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Note, User


async def get_owned_note(
    db: AsyncSession, note_id: int, user: User
) -> Note:
    """Return the note if owned by user; raise 404 otherwise.

    404 (not 403) so callers cannot distinguish "note doesn't exist" from
    "note belongs to someone else" — avoids leaking existence of other users' notes.
    """
    note = await db.get(Note, note_id)
    if note is None or note.owner_id != user.id:
        raise HTTPException(status_code=404, detail=f"Note {note_id} not found")
    return note