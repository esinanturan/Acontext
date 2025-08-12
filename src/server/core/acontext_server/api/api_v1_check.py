from fastapi import APIRouter
from ..schema.pydantic.api.response import BasicResponse
from ..schema.pydantic.result import Result, Error, Code
from ..client.db import DB_CLIENT
from ..client.redis import REDIS_CLIENT

V1_CHECK_ROUTER = APIRouter()


@V1_CHECK_ROUTER.get("/ping", tags=["chore"])
async def ping() -> BasicResponse:
    return Result.resolve({"message": "pong"}).to_response(BasicResponse)


@V1_CHECK_ROUTER.get("/health", tags=["chore"])
async def health() -> BasicResponse:
    if not await DB_CLIENT.health_check():
        return Result.reject(
            Code.SERVICE_UNAVAILABLE, "Database connection failed"
        ).to_response(BasicResponse)
    if not await REDIS_CLIENT.health_check():
        return Result.reject(
            Code.SERVICE_UNAVAILABLE, "Redis connection failed"
        ).to_response(BasicResponse)
    return Result.resolve({"message": "ok"}).to_response(BasicResponse)
