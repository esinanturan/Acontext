"""
Tests for Redis utility functions used by the skill learner.

Covers:
- push_skill_learn_pending stores item in Redis list
- drain_skill_learn_pending returns all items and clears list atomically
- drain_skill_learn_pending returns empty list when key doesn't exist
- renew_redis_lock refreshes TTL when lock exists (XX flag)
- renew_redis_lock does nothing when lock doesn't exist
"""

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from acontext_core.schema.mq.learning import SkillLearnDistilled
from acontext_core.service.utils import (
    push_skill_learn_pending,
    drain_skill_learn_pending,
    renew_redis_lock,
)


def _make_distilled(project_id=None, learning_space_id=None):
    return SkillLearnDistilled(
        project_id=project_id or uuid.uuid4(),
        session_id=uuid.uuid4(),
        task_id=uuid.uuid4(),
        learning_space_id=learning_space_id or uuid.uuid4(),
        distilled_context="## Task Analysis\nTest context",
    )


class TestPushSkillLearnPending:
    @pytest.mark.asyncio
    async def test_rpush_called_with_correct_key_and_value(self):
        """push_skill_learn_pending calls RPUSH with the correct key format."""
        project_id = uuid.uuid4()
        ls_id = uuid.uuid4()
        body_json = '{"test": "data"}'

        mock_client = AsyncMock()

        with patch(
            "acontext_core.service.utils.REDIS_CLIENT"
        ) as mock_redis:
            mock_redis.get_client_context.return_value.__aenter__ = AsyncMock(
                return_value=mock_client
            )
            mock_redis.get_client_context.return_value.__aexit__ = AsyncMock(
                return_value=False
            )

            await push_skill_learn_pending(project_id, ls_id, body_json)

            expected_key = f"skill_learn_pending.{project_id}.{ls_id}"
            mock_client.rpush.assert_called_once_with(expected_key, body_json)


def _make_pipeline_ctx(mock_pipe):
    """Build a mock that works as both `client.pipeline(...)` return and async context manager."""
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_pipe)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx


class TestDrainSkillLearnPending:
    @pytest.mark.asyncio
    async def test_returns_deserialized_items(self):
        """drain_skill_learn_pending deserializes all items from Redis list."""
        project_id = uuid.uuid4()
        ls_id = uuid.uuid4()

        item1 = _make_distilled(project_id=project_id, learning_space_id=ls_id)
        item2 = _make_distilled(project_id=project_id, learning_space_id=ls_id)

        mock_pipe = MagicMock()
        mock_pipe.execute = AsyncMock(
            return_value=[
                [item1.model_dump_json(), item2.model_dump_json()],
                1,
            ]
        )

        mock_client = MagicMock()
        mock_client.pipeline.return_value = _make_pipeline_ctx(mock_pipe)

        with patch(
            "acontext_core.service.utils.REDIS_CLIENT"
        ) as mock_redis:
            mock_redis.get_client_context.return_value.__aenter__ = AsyncMock(
                return_value=mock_client
            )
            mock_redis.get_client_context.return_value.__aexit__ = AsyncMock(
                return_value=False
            )

            result = await drain_skill_learn_pending(project_id, ls_id)

            assert len(result) == 2
            assert result[0].session_id == item1.session_id
            assert result[1].session_id == item2.session_id

    @pytest.mark.asyncio
    async def test_returns_empty_when_key_missing(self):
        """drain_skill_learn_pending returns empty list when Redis key doesn't exist."""
        project_id = uuid.uuid4()
        ls_id = uuid.uuid4()

        mock_pipe = MagicMock()
        mock_pipe.execute = AsyncMock(return_value=[[], 0])

        mock_client = MagicMock()
        mock_client.pipeline.return_value = _make_pipeline_ctx(mock_pipe)

        with patch(
            "acontext_core.service.utils.REDIS_CLIENT"
        ) as mock_redis:
            mock_redis.get_client_context.return_value.__aenter__ = AsyncMock(
                return_value=mock_client
            )
            mock_redis.get_client_context.return_value.__aexit__ = AsyncMock(
                return_value=False
            )

            result = await drain_skill_learn_pending(project_id, ls_id)

            assert result == []

    @pytest.mark.asyncio
    async def test_uses_transactional_pipeline(self):
        """drain_skill_learn_pending uses MULTI/EXEC (transaction=True) for atomicity."""
        project_id = uuid.uuid4()
        ls_id = uuid.uuid4()

        mock_pipe = MagicMock()
        mock_pipe.execute = AsyncMock(return_value=[[], 0])

        mock_client = MagicMock()
        mock_client.pipeline.return_value = _make_pipeline_ctx(mock_pipe)

        with patch(
            "acontext_core.service.utils.REDIS_CLIENT"
        ) as mock_redis:
            mock_redis.get_client_context.return_value.__aenter__ = AsyncMock(
                return_value=mock_client
            )
            mock_redis.get_client_context.return_value.__aexit__ = AsyncMock(
                return_value=False
            )

            await drain_skill_learn_pending(project_id, ls_id)

            mock_client.pipeline.assert_called_once_with(transaction=True)


class TestRenewRedisLock:
    @pytest.mark.asyncio
    async def test_refreshes_ttl_with_xx_flag(self):
        """renew_redis_lock calls SET with XX and EX flags."""
        project_id = uuid.uuid4()
        mock_client = AsyncMock()
        mock_client.set = AsyncMock(return_value=True)

        with patch(
            "acontext_core.service.utils.REDIS_CLIENT"
        ) as mock_redis:
            mock_redis.get_client_context.return_value.__aenter__ = AsyncMock(
                return_value=mock_client
            )
            mock_redis.get_client_context.return_value.__aexit__ = AsyncMock(
                return_value=False
            )

            result = await renew_redis_lock(project_id, "skill_learn.test", 240)

            assert result is True
            mock_client.set.assert_called_once_with(
                f"lock.{project_id}.skill_learn.test",
                "1",
                xx=True,
                ex=240,
            )

    @pytest.mark.asyncio
    async def test_returns_false_when_lock_expired(self):
        """renew_redis_lock returns False when lock doesn't exist (XX fails)."""
        project_id = uuid.uuid4()
        mock_client = AsyncMock()
        mock_client.set = AsyncMock(return_value=None)

        with patch(
            "acontext_core.service.utils.REDIS_CLIENT"
        ) as mock_redis:
            mock_redis.get_client_context.return_value.__aenter__ = AsyncMock(
                return_value=mock_client
            )
            mock_redis.get_client_context.return_value.__aexit__ = AsyncMock(
                return_value=False
            )

            result = await renew_redis_lock(project_id, "skill_learn.test", 240)

            assert result is False
