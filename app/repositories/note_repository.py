from sqlalchemy.orm import Session
from app.models import Note as NoteModel


def get_note(db: Session, note_id: int, user_id: int):
    return (
        db.query(NoteModel)
        .filter(
            NoteModel.id == note_id,
            NoteModel.owner_id == user_id,
        )
        .first()
    )


def get_notes(db: Session, user_id: int):
    return (
        db.query(NoteModel)
        .filter(NoteModel.owner_id == user_id)
        .all()
    )

def create_note(db: Session, note: NoteModel):
    db.add(note)
    db.flush()
    db.refresh(note)

    return note

def update_note(db: Session, note_id: int, title: str, content: str, user_id: int):

    note = (
        db.query(NoteModel)
        .filter(
            NoteModel.id == note_id,
            NoteModel.owner_id == user_id,
        )
        .first()
    )

    if note is None:
        return None

    note.title = title
    note.content = content

    db.commit()
    db.refresh(note)

    return note

def delete_note(db: Session, note_id: int, user_id: int):
    note = (
        db.query(NoteModel)
        .filter(
            NoteModel.id == note_id,
            NoteModel.owner_id == user_id,
        )
        .first()
    )

    if note is None:
        return None

    db.delete(note)
    db.commit()

    return note
