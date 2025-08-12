from fastapi import APIRouter, Request, Body, Query
from ..schema.pydantic.api.basic import BasicResponse
from ..schema.pydantic.api.v1.response import (
    MQTaskData,
    SessionMessageStatusCheck,
    SessionTasks,
)
from ..schema.pydantic.api.v1.request import (
    LocateProject,
    LocateSession,
    SessionPushOpenAIMessage,
    SessionGetScratchpad,
    SessionTasksParams,
)

V1_SESSION_ROUTER = APIRouter()


@V1_SESSION_ROUTER.post("/create_session")
def create_session(
    request: Request,
    body: LocateProject = Body(...),
) -> BasicResponse[LocateSession]:
    """Create a new session for a project"""
    pass


@V1_SESSION_ROUTER.post("/push_openai_messages")
def push_openai_messages_to_session(
    request: Request,
    body: SessionPushOpenAIMessage = Body(...),
) -> BasicResponse[MQTaskData]:
    """Push OpenAI-format messages into this session"""
    pass


@V1_SESSION_ROUTER.post("/close_session")
def close_session(
    request: Request,
    body: LocateSession = Body(...),
) -> BasicResponse[bool]:
    """Once the session is closed, acontext will:
    1. process the leftover messages in this session
    2. start to sync experiences with parent space
    3. run some stats into db
    """
    pass


@V1_SESSION_ROUTER.get("/session_scratchpad")
def get_session_scratchpad(
    request: Request,
    param: SessionGetScratchpad = Query(...),
) -> BasicResponse[str]:
    """A helper function to pack all the session context so far into a meaningful string"""
    return BasicResponse[str](
        data="Hello",
        status=200,
        errmsg="",
    )


@V1_SESSION_ROUTER.get("/check_messages_status")
def check_messages_status(
    request: Request,
    param: LocateSession = Query(...),
) -> BasicResponse[SessionMessageStatusCheck]:
    pass


@V1_SESSION_ROUTER.get("/fetch_tasks")
def fetch_tasks(
    request: Request,
    param: SessionTasksParams = Query(...),
) -> BasicResponse[SessionTasks]:
    pass
