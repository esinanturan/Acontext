from pydantic import BaseModel, Field
from typing import Literal, Optional


class OpenAIFunction(BaseModel):
    name: str
    arguments: Optional[str] = None


class OpenAIToolCall(BaseModel):
    id: str
    function: Optional[OpenAIFunction] = None
    type: Literal["function", "tool"]


class OpenAIMessageBlob(BaseModel):
    role: Literal["user", "assistant", "system", "tool"]
    content: str
    function_call: Optional[OpenAIToolCall] = None
    tool_calls: Optional[list[OpenAIToolCall]] = None
    tool_call_id: Optional[str] = None


class OpenAIMessages(BaseModel):
    messages: list[OpenAIMessageBlob] = Field(
        ..., description="openai chat.completion message format"
    )
