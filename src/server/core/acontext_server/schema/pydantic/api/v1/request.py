from pydantic import BaseModel, Field
from typing import Optional
from typing import Any
from enum import StrEnum
from ...message.openai import OpenAIMessages
from ...utils import UUID
from .data import BlockType


class Pagination(BaseModel):
    limit: int = Field(20, description="limit of the pagination. 0 means no limit")
    offset: int = Field(0, description="offset of the pagination")


class JSONConfig(BaseModel):
    configs: dict[str, Any] = Field(..., description="JSON for configs or properties")


class JSONProperty(BaseModel):
    properties: dict[str, Any] = Field(..., description="JSON for properties")


class SemanticQuery(BaseModel):
    query: str


class LocateSession(BaseModel):
    session_id: UUID = Field(..., description="id of the session")


class LocateSpace(BaseModel):
    space_id: UUID = Field(..., description="id of the space")


class LocateSpacePage(BaseModel):
    space_id: UUID = Field(..., description="id of the space")
    page_id: UUID = Field(..., description="id of the page")


class LocateSpaceParentPage(BaseModel):
    space_id: UUID = Field(..., description="id of the space")
    par_page_id: Optional[UUID] = Field(..., description="id of the parent page")


class LocateSpaceBlock(BaseModel):
    space_id: UUID = Field(..., description="id of the space")
    block_id: UUID = Field(..., description="id of the page")


class SpaceFind(LocateSpace, SemanticQuery):
    pass


class SpaceCreatePage(JSONProperty):
    par_page_id: Optional[UUID] = Field(..., description="id of the parent page")


class SpaceCreateBlock(JSONProperty):
    block_type: BlockType
    par_page_id: Optional[UUID] = Field(..., description="id of the parent page")
    par_block_id: Optional[UUID] = Field(
        ...,
        description="id of the parent block. Either `par_page_id` or `par_block_id` is not null",
    )


class SessionConnectToSpace(LocateSpace):
    pass


class SessionUpdateConfig(LocateSession, JSONConfig):
    pass


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
