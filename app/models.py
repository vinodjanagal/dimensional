from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime



class Base(DeclarativeBase):
    pass

class Note(Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(primary_key=True)

    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable= False
    )

    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default= datetime.utcnow,
        nullable= False
        )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
    

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key= True)
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )


    


