from sqlalchemy.orm import Session
from app.repositories import note_repository
from app.models import Note as NoteModel


def get_note(db: Session, note_id: int, user_id: int):
    return note_repository.get_note(db, note_id, user_id)


def get_notes(db: Session, user_id: int):
    return note_repository.get_notes(db, user_id)


def create_note(db: Session, title:str, content:str, user_id: int):

    note = NoteModel(
        title=title,
        content=content,
        owner_id=user_id,
    )

    try:
        note = note_repository.create_note(db, note)
        db.commit()
        return note

    except Exception:
        db.rollback()
        raise
        

def update_note(
    db: Session,
    note_id: int,
    title: str,
    content: str,
    user_id: int,
):
    return note_repository.update_note(
        db,
        note_id,
        title,
        content,
        user_id,
    )


def delete_note(db:Session, note_id: int, user_id: int):
    return note_repository.delete_note(
        db, 
        note_id, 
        user_id,
    )






