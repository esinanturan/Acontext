from typing import Any
from ....infra.db import AsyncSession
from ..base import Tool, ToolPool
from ....schema.llm import ToolSchema
from ....schema.utils import asUUID
from ....schema.result import Result
from ....schema.orm import Task
from ....service.data import task as TD
from ....env import LOG
from .ctx import TaskCtx


async def _append_messages_to_task_handler(
    ctx: TaskCtx,
    llm_arguments: dict,
) -> Result[str]:
    task_order = llm_arguments.get("task_order", None)
    message_order_indexes = llm_arguments.get("message_ids", [])
    if not task_order:
        return Result.resolve(
            f"You must provide a task order argument, so that we can attach messages to the task. Appending failed."
        )
    if task_order > len(ctx.task_ids_index) or task_order < 1:
        return Result.resolve(
            f"Task order {task_order} is out of range, appending failed."
        )
    actually_task_id = ctx.task_ids_index[task_order - 1]
    actually_message_ids = [
        ctx.message_ids_index[i]
        for i in message_order_indexes
        if i < len(ctx.message_ids_index)
    ]
    if not actually_message_ids:
        return Result.resolve(
            f"No message ids to append, skip: {message_order_indexes}"
        )
    r = await TD.append_messages_to_task(
        ctx.db_session,
        actually_message_ids,
        actually_task_id,
    )
    return (
        Result.resolve(
            f"Messages {message_order_indexes} appended to task {task_order}"
        )
        if r.ok()
        else r
    )


_append_messages_to_task_tool = (
    Tool()
    .use_schema(
        ToolSchema(
            function={
                "name": "append_messages_to_task",
                "description": """Link current message ids to a task for tracking progress and context.
Use this to associate conversation messages with relevant tasks.
If the task is marked as 'success' or 'failed', don't append messages to it.""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_order": {
                            "type": "integer",
                            "description": "The order number of the task to link messages to.",
                        },
                        "message_ids": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "List of message IDs to append to the task.",
                        },
                    },
                    "required": ["task_order", "message_ids"],
                },
            }
        )
    )
    .use_handler(_append_messages_to_task_handler)
)
