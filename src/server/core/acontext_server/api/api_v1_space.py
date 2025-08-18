from fastapi import APIRouter, Request, Body, Query
from ..schema.pydantic.api.basic import BasicResponse
from ..schema.pydantic.api.v1.request import (
    UUID,
    JSONConfig,
    LocateSpace,
    SpaceFind,
)
from ..schema.pydantic.api.v1.response import SimpleId, SpaceStatusCheck

V1_SPACE_ROUTER = APIRouter()


@V1_SPACE_ROUTER.post("/")
def create_space(
    request: Request,
    body: JSONConfig = Body(...),
) -> BasicResponse[SimpleId]:
    """Create a new space for a project"""
    pass


@V1_SPACE_ROUTER.delete("/{space_id}")
def delete_space(request: Request, space_id: UUID) -> BasicResponse[bool]:
    """delete for a project"""
    pass


@V1_SPACE_ROUTER.put("/{space_id}/configs")
def update_space_config(
    request: Request,
    space_id: UUID,
    body: JSONConfig = Body(...),
) -> BasicResponse[bool]:
    """update the config of a space"""
    pass


@V1_SPACE_ROUTER.get("/{space_id}/configs")
def get_space_config(request: Request, space_id: UUID) -> BasicResponse[JSONConfig]:
    """get the config of a space"""
    pass


@V1_SPACE_ROUTER.get("/check_space_status")
def check_space_status(
    request: Request,
    param: LocateSpace = Query(...),
) -> BasicResponse[SpaceStatusCheck]:
    pass


@V1_SPACE_ROUTER.get("/semantic_answer")
def find_experiences_in_space(
    request: Request,
    body: SpaceFind = Query(...),
) -> BasicResponse[str]:
    """find experiences and answer query"""
    pass


@V1_SPACE_ROUTER.get("/semantic_glob")
def glob_pages_by_query(
    request: Request,
    body: SpaceFind = Query(...),
) -> BasicResponse[str]:
    """find experiences in a space"""
    pass


@V1_SPACE_ROUTER.get("/semantic_grep")
def grep_blocks_by_query(
    request: Request,
    body: SpaceFind = Query(...),
) -> BasicResponse[str]:
    """find experiences in a space"""
    pass
