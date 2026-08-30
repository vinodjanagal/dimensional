from pydantic import BaseModel
from datetime import datetime

class NoteCreate(BaseModel):
    title: str
    content: str
    

class NoteResponse(BaseModel):
    id: int
    title: str
    content: str
    owner_id:int
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }

    