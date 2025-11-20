from ..base import Tool
from ....schema.llm import ToolSchema


_finish_tool = Tool().use_schema(
    ToolSchema(
        function={
            "name": "finish",
            "description": "Call it when you have completed everything you need to do in this workspace.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        }
    )
)
