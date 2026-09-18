"""add note owner

Revision ID: cd62a9130ea6
Revises: c076a9935526
Create Date: 2026-08-26 17:36:19.846123

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cd62a9130ea6'
down_revision: Union[str, Sequence[str], None] = 'c076a9935526'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('notes', sa.Column('owner_id', sa.Integer(), nullable=False))
    op.create_foreign_key(
        "fk_notes_owner_id_users",
        "notes",
        "users",
        ["owner_id"],
        ["id"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "fk_notes_owner_id_users",
        "notes",
        type_="foreignkey",
    )
    op.drop_column('notes', 'owner_id')