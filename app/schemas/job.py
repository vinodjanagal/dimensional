from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class JobResponse(BaseModel):
    id: UUID
    note_id: int
    job_type: str
    status: str
    result: dict | None
    error: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None

    model_config = {"from_attributes": True}


class JobEnqueuedResponse(BaseModel):
    job_id: UUID
    status: str