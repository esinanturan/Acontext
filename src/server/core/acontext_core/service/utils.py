from typing import List

from ..infra.redis import REDIS_CLIENT
from ..env import DEFAULT_CORE_CONFIG
from ..schema.utils import asUUID
from ..schema.mq.learning import SkillLearnDistilled


async def check_redis_lock_or_set(
    project_id: asUUID, key: str, ttl_seconds: int | None = None
) -> bool:
    new_key = f"lock.{project_id}.{key}"
    async with REDIS_CLIENT.get_client_context() as client:
        # Use SET with NX (not exists) and EX (expire) for atomic lock acquisition
        result = await client.set(
            new_key,
            "1",
            nx=True,  # Only set if key doesn't exist
            ex=(
                ttl_seconds
                if ttl_seconds is not None
                else DEFAULT_CORE_CONFIG.session_message_processing_timeout_seconds
            ),
        )
        # Returns True if the lock was acquired (key didn't exist), False if it already existed
        return result is not None


async def release_redis_lock(project_id: asUUID, key: str):
    new_key = f"lock.{project_id}.{key}"
    async with REDIS_CLIENT.get_client_context() as client:
        await client.delete(new_key)


async def renew_redis_lock(project_id: asUUID, key: str, ttl_seconds: int) -> bool:
    """Refresh lock TTL only if the lock still exists (XX flag).

    Returns True if the lock was renewed, False if it had already expired.
    """
    new_key = f"lock.{project_id}.{key}"
    async with REDIS_CLIENT.get_client_context() as client:
        result = await client.set(new_key, "1", xx=True, ex=ttl_seconds)
        return result is not None


async def push_skill_learn_pending(
    project_id: asUUID, learning_space_id: asUUID, body_json: str
) -> None:
    """Append a SkillLearnDistilled JSON to the pending list for this learning space."""
    key = f"skill_learn_pending.{project_id}.{learning_space_id}"
    async with REDIS_CLIENT.get_client_context() as client:
        await client.rpush(key, body_json)


async def drain_skill_learn_pending(
    project_id: asUUID,
    learning_space_id: asUUID,
    max_read: int | None = None,
) -> List[SkillLearnDistilled]:
    """Atomically read and remove pending items for this learning space.

    Uses MULTI/EXEC to prevent a race where an item pushed between the read
    and remove would be silently lost.

    When *max_read* is set, only the first *max_read* items are consumed and
    the remainder stays in the list for the next drain.
    """
    if max_read is not None and max_read <= 0:
        return []
    key = f"skill_learn_pending.{project_id}.{learning_space_id}"
    async with REDIS_CLIENT.get_client_context() as client:
        async with client.pipeline(transaction=True) as pipe:
            if max_read is None:
                pipe.lrange(key, 0, -1)
                pipe.delete(key)
            else:
                pipe.lrange(key, 0, max_read - 1)
                pipe.ltrim(key, max_read, -1)
            results = await pipe.execute()
    items = results[0]
    return [SkillLearnDistilled.model_validate_json(item) for item in items]


async def check_buffer_timer_or_set(
    project_id: asUUID, session_id: asUUID, ttl_seconds: int
) -> bool:
    """
    Check if a buffer timer already exists for this session. If not, set one.

    Returns True if the key was newly set (caller should create the timer),
    False if the key already existed (timer already scheduled).
    """
    key = f"buffer_timer.{project_id}.{session_id}"
    async with REDIS_CLIENT.get_client_context() as client:
        result = await client.set(
            key,
            "1",
            nx=True,
            ex=ttl_seconds,
        )
        return result is not None
