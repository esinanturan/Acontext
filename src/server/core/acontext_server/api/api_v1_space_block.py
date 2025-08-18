from fastapi import APIRouter, Request, Body, Query
from ..schema.pydantic.api.basic import BasicResponse
from ..schema.pydantic.api.v1.request import (
    UUID,
    JSONConfig,
    SpaceCreateBlock,
    JSONProperty,
)
from ..schema.pydantic.api.v1.response import SimpleId, SpaceStatusCheck

V1_SPACE_BLOCK_ROUTER = APIRouter()


@V1_SPACE_BLOCK_ROUTER.post("/")
def create_block(
    request: Request, space_id: UUID, body: SpaceCreateBlock = Body(...)
) -> BasicResponse[SimpleId]:
    pass


@V1_SPACE_BLOCK_ROUTER.delete("/{block_id}")
def delete_block(
    request: Request, space_id: UUID, block_id: UUID
) -> BasicResponse[bool]:
    pass


@V1_SPACE_BLOCK_ROUTER.get("/{block_id}/properties")
def get_block_properties(
    request: Request, space_id: UUID, block_id: UUID
) -> BasicResponse[JSONProperty]:
    pass


@V1_SPACE_BLOCK_ROUTER.put("/{block_id}/properties/{property_key}")
def update_block_properties_by_key(
    request: Request,
    space_id: UUID,
    block_id: UUID,
    property_key: str,
    body: JSONProperty = Body(...),
) -> BasicResponse[bool]:
    pass


# @V1_SPACE_PAGE_ROUTER.get("/{page_id}/properties")
# def get_page_properties(
#     request: Request, space_id: UUID, page_id: UUID
# ) -> BasicResponse[JSONConfig]:
#     pass
