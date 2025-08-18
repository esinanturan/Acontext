from pydantic import BaseModel
from typing import Optional, TypeVar, Generic
from ..error_code import Code

T = TypeVar("T", dict, BaseModel)


class BasicResponse(BaseModel, Generic[T]):
    data: Optional[T] = None
    status: Code = Code.SUCCESS
    errmsg: str = ""
