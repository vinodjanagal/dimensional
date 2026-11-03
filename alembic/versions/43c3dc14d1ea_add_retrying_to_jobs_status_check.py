"""add_retrying_to_jobs_status_check

Revision ID: 43c3dc14d1ea
Revises: a8304b91401f
Create Date: 2026-11-03 20:51:05.622894

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '43c3dc14d1ea'
down_revision: Union[str, Sequence[str], None] = 'a8304b91401f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: allow 'retrying' status in ck_jobs_status."""
    op.drop_constraint("ck_jobs_status", "jobs", type_="check")
    op.create_check_constraint(
        "ck_jobs_status",
        "jobs",
        "status IN ('queued', 'running', 'retrying', 'done', 'failed')",
    )


def downgrade() -> None:
    """Downgrade schema: reconcile active 'retrying' rows before reverting constraint."""
    op.drop_constraint("ck_jobs_status", "jobs", type_="check")
    
    # Data reconciliation: reset any 'retrying' jobs back to 'queued'
    # so the narrower constraint does not raise a check violation on existing data.
    op.execute("UPDATE jobs SET status = 'queued' WHERE status = 'retrying'")
    
    op.create_check_constraint(
        "ck_jobs_status",
        "jobs",
        "status IN ('queued', 'running', 'done', 'failed')",
    )