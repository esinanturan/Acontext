from pydantic import BaseModel
from datetime import datetime
from uuid import UUID


class ProjectRow(BaseModel):
    configs: dict


class SpaceRow(BaseModel):
    configs: dict
