from pydantic import BaseModel, Field
from typing import Optional
from enum import StrEnum
from ...message.openai import OpenAIMessages
from ...utils import UUID


class LocateProject(BaseModel):
    project_id: UUID = Field(..., description="id of the project")


class LocateSession(BaseModel):
    session_id: UUID = Field(..., description="id of the session")
    project_id: UUID = Field(..., description="id of the project")


class SessionTasksParams(BaseModel):
    last_task_num: Optional[int] = Field(
        None,
        description="last task number of the scratchpad. None means all tasks",
    )

    exclude_failed_tasks: bool = Field(
        False,
        description="exclude failed tasks in the scratchpad",
    )
    exclude_finished_tasks: bool = Field(
        False,
        description="exclude finished tasks in the scratchpad",
    )


class SessionScratchpadParams(SessionTasksParams):
    max_token_size: int = Field(1024, description="max token size of the scratchpad")
    wait_for_message_process: bool = Field(
        False,
        description="wait for unprocessed messages to finish before returning the scratchpad",
    )


class SessionPushOpenAIMessage(OpenAIMessages, LocateSession):
    pass


class SessionGetScratchpad(LocateSession, SessionScratchpadParams):
    pass
