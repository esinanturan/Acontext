from pydantic import BaseModel
from ...utils import UUID
from .data import SessionMessageStatus, SessionTaskStatus


class MQTaskData(BaseModel):
    task_id: UUID


class SessionMessageStatusCheck(BaseModel):
    pending: int
    processing: int
    completed: int
    failed: int


class SessionTask(BaseModel):
    task_step: int
    task_name: str
    task_description: str
    task_status: SessionTaskStatus
    learned_hints: list[str]
    failed_attempts: list[str]


class SessionTasks(BaseModel):
    plan: str
    tasks: list[SessionTask]
