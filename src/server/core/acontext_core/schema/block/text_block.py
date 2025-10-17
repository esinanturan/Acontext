from pydantic import BaseModel
from typing import List, Optional
from ..utils import asUUID


class TextData(BaseModel):
    use_when: str
    notes: str


class TextBlock(TextData):
    id: asUUID
    space_id: asUUID
