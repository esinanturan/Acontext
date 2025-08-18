from enum import StrEnum


class SessionMessageStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class SessionTaskStatus(StrEnum):
    unchecked = "unchecked"
    checked = "checked"
    FAILED = "failed"


class BlockType(StrEnum):
    TEXT = "text"
    WORKFLOW = "workflow"
