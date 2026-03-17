"""
Integration-style test for the skill learner retrigger chain under concurrent load.

Simulates N sessions arriving concurrently at the agent consumer — only one
wins the Redis lock, the rest push to a fake pending list. The agent fails on
the first cycle, but the retrigger in `finally` ensures the chain is never
broken and all sessions eventually reach a terminal state.
"""

import uuid
from contextlib import ExitStack
from typing import List

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from acontext_core.schema.result import Result
from acontext_core.schema.mq.learning import SkillLearnDistilled
from acontext_core.service.skill_learner import process_skill_agent


def _make_distilled_body(
    project_id=None,
    session_id=None,
    learning_space_id=None,
) -> SkillLearnDistilled:
    return SkillLearnDistilled(
        project_id=project_id or uuid.uuid4(),
        session_id=session_id or uuid.uuid4(),
        task_id=uuid.uuid4(),
        learning_space_id=learning_space_id or uuid.uuid4(),
        distilled_context="## Task Analysis (Success)\nTest distilled context",
    )


class FakeRedisState:
    """Simulates Redis lock + pending list used by the skill learner consumer."""

    def __init__(self):
        self.pending: List[SkillLearnDistilled] = []
        self.lock_held = False
        self.status_tracker: dict[uuid.UUID, str] = {}
        self.publish_calls: List[str] = []
        self.agent_call_count = 0

    async def check_lock(self, pid, key, ttl_seconds=None):
        if self.lock_held:
            return False
        self.lock_held = True
        return True

    async def release_lock(self, pid, key):
        self.lock_held = False

    async def push_pending(self, pid, ls, json_str):
        self.pending.append(SkillLearnDistilled.model_validate_json(json_str))

    async def drain_pending(self, pid, ls, max_read=1):
        result = []
        for _ in range(min(max_read, len(self.pending))):
            result.append(self.pending.pop(0))
        return result

    async def update_status(self, db, sid, status):
        self.status_tracker[sid] = status

    async def publish(self, **kwargs):
        self.publish_calls.append(kwargs["body"])

    async def agent_fail_then_succeed(self, pid, ls, context, **kwargs):
        """First call rejects (simulating failure); subsequent calls succeed
        and drain all remaining pending items (simulating agent entry drain)."""
        self.agent_call_count += 1
        if self.agent_call_count == 1:
            return Result.reject("Agent crashed on cycle 1")
        drained_ids = [item.session_id for item in self.pending]
        self.pending.clear()
        return Result.resolve(drained_ids)


class TestConcurrentSessionsScenario:
    """
    End-to-end retrigger chain: N sessions, 1 lock winner, agent failure,
    then recovery. Verifies no session stays 'queued' forever.
    """

    def _build_patches(self, state: FakeRedisState):
        return (
            patch("acontext_core.service.skill_learner.DB_CLIENT"),
            patch(
                "acontext_core.service.skill_learner.check_redis_lock_or_set",
                new_callable=AsyncMock,
                side_effect=state.check_lock,
            ),
            patch(
                "acontext_core.service.skill_learner.release_redis_lock",
                new_callable=AsyncMock,
                side_effect=state.release_lock,
            ),
            patch(
                "acontext_core.service.skill_learner.push_skill_learn_pending",
                new_callable=AsyncMock,
                side_effect=state.push_pending,
            ),
            patch(
                "acontext_core.service.skill_learner.drain_skill_learn_pending",
                new_callable=AsyncMock,
                side_effect=state.drain_pending,
            ),
            patch(
                "acontext_core.service.skill_learner.LS.update_session_status",
                new_callable=AsyncMock,
                side_effect=state.update_status,
            ),
            patch(
                "acontext_core.service.skill_learner.publish_mq",
                new_callable=AsyncMock,
                side_effect=state.publish,
            ),
            patch(
                "acontext_core.service.skill_learner.SLC.run_skill_agent",
                new_callable=AsyncMock,
                side_effect=state.agent_fail_then_succeed,
            ),
        )

    def _setup_db(self, mock_db):
        mock_db.get_session_context.return_value.__aenter__ = AsyncMock(
            return_value=MagicMock()
        )
        mock_db.get_session_context.return_value.__aexit__ = AsyncMock(
            return_value=False
        )

    @pytest.mark.asyncio
    async def test_no_session_stuck_after_agent_failure(self):
        """5 concurrent sessions: agent fails on cycle 1, retrigger chain
        recovers all remaining sessions — none stay 'queued'."""
        project_id = uuid.uuid4()
        ls_id = uuid.uuid4()
        sessions = [
            _make_distilled_body(project_id=project_id, learning_space_id=ls_id)
            for _ in range(5)
        ]

        state = FakeRedisState()

        with ExitStack() as stack:
            mocks = [stack.enter_context(p) for p in self._build_patches(state)]
            mock_db = mocks[0]
            self._setup_db(mock_db)

            # Phase 1 — 4 losers arrive while lock is held
            state.lock_held = True
            for s in sessions[1:]:
                await process_skill_agent(s, MagicMock())

            assert len(state.pending) == 4
            for s in sessions[1:]:
                assert state.status_tracker[s.session_id] == "queued"

            # Phase 2 — lock winner processes (agent fails on cycle 1)
            state.lock_held = False
            await process_skill_agent(sessions[0], MagicMock())

            # Phase 3 — follow the retrigger chain until done
            while state.publish_calls:
                body_json = state.publish_calls.pop(0)
                body = SkillLearnDistilled.model_validate_json(body_json)
                await process_skill_agent(body, MagicMock())

        # Every session reached a terminal state
        all_sids = {s.session_id for s in sessions}
        tracked_sids = set(state.status_tracker.keys())
        assert all_sids == tracked_sids, (
            f"Missing status for: {all_sids - tracked_sids}"
        )
        for sid, status in state.status_tracker.items():
            assert status in ("completed", "failed"), (
                f"Session {sid} stuck in '{status}'"
            )

        # At least one failed (cycle 1) and at least one completed (cycle 2+)
        statuses = set(state.status_tracker.values())
        assert "failed" in statuses
        assert "completed" in statuses

        # Retrigger chain was not broken
        assert state.agent_call_count >= 2

        # Pending list fully drained
        assert len(state.pending) == 0

    @pytest.mark.asyncio
    async def test_retrigger_chain_processes_large_batch(self):
        """20 concurrent sessions: verifies the retrigger chain scales beyond
        a single agent's max_contexts capacity (4), requiring multiple cycles."""
        project_id = uuid.uuid4()
        ls_id = uuid.uuid4()
        n = 20
        sessions = [
            _make_distilled_body(project_id=project_id, learning_space_id=ls_id)
            for _ in range(n)
        ]

        state = FakeRedisState()

        # Agent always succeeds (no failure cycle)
        async def agent_always_succeed(pid, ls, context, **kwargs):
            state.agent_call_count += 1
            max_drain = 4
            drained_ids = [
                item.session_id
                for item in state.pending[:max_drain]
            ]
            del state.pending[:max_drain]
            return Result.resolve(drained_ids)

        all_patches = list(self._build_patches(state))
        all_patches[-1] = patch(
            "acontext_core.service.skill_learner.SLC.run_skill_agent",
            new_callable=AsyncMock,
            side_effect=agent_always_succeed,
        )

        with ExitStack() as stack:
            mocks = [stack.enter_context(p) for p in all_patches]
            mock_db = mocks[0]
            self._setup_db(mock_db)

            # All but the first lose the lock
            state.lock_held = True
            for s in sessions[1:]:
                await process_skill_agent(s, MagicMock())
            assert len(state.pending) == n - 1

            # Lock winner kicks off chain
            state.lock_held = False
            await process_skill_agent(sessions[0], MagicMock())

            while state.publish_calls:
                body_json = state.publish_calls.pop(0)
                body = SkillLearnDistilled.model_validate_json(body_json)
                await process_skill_agent(body, MagicMock())

        # All sessions completed
        all_sids = {s.session_id for s in sessions}
        for sid in all_sids:
            status = state.status_tracker.get(sid)
            assert status == "completed", (
                f"Session {sid} has status '{status}', expected 'completed'"
            )

        # Required multiple agent cycles
        assert state.agent_call_count >= 2

        # Nothing left behind
        assert len(state.pending) == 0

    @pytest.mark.asyncio
    async def test_chain_survives_multiple_consecutive_failures(self):
        """Agent fails 3 times in a row, then succeeds. The retrigger chain
        in finally ensures every failure still triggers the next cycle."""
        project_id = uuid.uuid4()
        ls_id = uuid.uuid4()
        sessions = [
            _make_distilled_body(project_id=project_id, learning_space_id=ls_id)
            for _ in range(5)
        ]

        state = FakeRedisState()
        failures_before_success = 3

        async def agent_fail_n_then_succeed(pid, ls, context, **kwargs):
            state.agent_call_count += 1
            if state.agent_call_count <= failures_before_success:
                return Result.reject(
                    f"Agent crashed on cycle {state.agent_call_count}"
                )
            drained_ids = [item.session_id for item in state.pending]
            state.pending.clear()
            return Result.resolve(drained_ids)

        all_patches = list(self._build_patches(state))
        all_patches[-1] = patch(
            "acontext_core.service.skill_learner.SLC.run_skill_agent",
            new_callable=AsyncMock,
            side_effect=agent_fail_n_then_succeed,
        )

        with ExitStack() as stack:
            mocks = [stack.enter_context(p) for p in all_patches]
            mock_db = mocks[0]
            self._setup_db(mock_db)

            state.lock_held = True
            for s in sessions[1:]:
                await process_skill_agent(s, MagicMock())

            state.lock_held = False
            await process_skill_agent(sessions[0], MagicMock())

            while state.publish_calls:
                body_json = state.publish_calls.pop(0)
                body = SkillLearnDistilled.model_validate_json(body_json)
                await process_skill_agent(body, MagicMock())

        # Agent ran once for original + 3 failed retriggers + 1 successful = 5
        # (but some retriggers consume from pending, reducing total cycles)
        assert state.agent_call_count >= failures_before_success + 1

        # No session stuck as 'queued'
        for sid, status in state.status_tracker.items():
            assert status in ("completed", "failed"), (
                f"Session {sid} stuck in '{status}'"
            )

        # At least some sessions completed
        completed = [
            s for s in sessions
            if state.status_tracker.get(s.session_id) == "completed"
        ]
        assert len(completed) >= 1

        # Pending fully drained
        assert len(state.pending) == 0
