from pydantic import BaseModel
from typing import List, Optional, Any
from ..utils import asUUID


class SOPStep(BaseModel):
    tool_name: str
    tool_arguments_with_placeholder: dict[str, Any]
    purpose_annotation: Optional[str] = None


class SOPData(BaseModel):
    use_when: str
    notes: str
    sop: List[SOPStep]


class SOPBlock(SOPData):
    id: asUUID
    space_id: asUUID
