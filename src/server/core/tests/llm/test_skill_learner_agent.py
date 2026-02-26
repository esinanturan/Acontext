"""
Tests for the skill learner agent loop (skill_learner_agent).

Covers:
- Multi-turn tool dispatch: agent reads skills, edits files, creates new skills
- Agent receives distilled context (not raw messages) in user message
- Agent stops on finish / no-tool / max_iterations
- Agent preserves has_reported_thinking across iterations
- Agent handles LLM error and tool error gracefully
- Redis drain on entry: picks up leftover pending contexts
- Redis drain between iterations: injects new user messages
- Finish overridden when pending contexts exist
- Finish honored when no pending contexts
- Agent returns Result[list[UUID]] with all drained session IDs on success
- Agent re-pushes all drained items to Redis on RuntimeError
- Lock TTL renewed between iterations
- max_iterations extended when new contexts arrive
- Context cap stops draining after max_contexts_per_agent_run
"""

import uuid
import pytest
from pydantic import BaseModel as PydanticBaseModel
from unittest.mock import AsyncMock, MagicMock, patch, call

from acontext_core.env import DEFAULT_CORE_CONFIG
from acontext_core.schema.result import Result
from acontext_core.schema.llm import LLMResponse, LLMToolCall, LLMFunction
from acontext_core.schema.mq.learning import SkillLearnDistilled
from acontext_core.service.data.learning_space import SkillInfo
from acontext_core.llm.agent.skill_learner import skill_learner_agent


class _FakeRaw(PydanticBaseModel):
    pass


def _llm(tool_calls=None, content=None):
    """Build a mock LLMResponse."""
    return LLMResponse(
        role="assistant",
        raw_response=_FakeRaw(),
        tool_calls=tool_calls,
        content=content,
    )


def _tc(name, arguments, call_id=None):
    """Shorthand to build a LLMToolCall."""
    return LLMToolCall(
        id=call_id or f"call_{name}_{uuid.uuid4().hex[:6]}",
        function=LLMFunction(name=name, arguments=arguments),
        type="function",
    )


def _make_skill_info(
    name="auth-patterns",
    description="Authentication best practices",
    file_paths=None,
):
    return SkillInfo(
        id=uuid.uuid4(),
        disk_id=uuid.uuid4(),
        name=name,
        description=description,
        file_paths=file_paths or ["SKILL.md"],
    )


def _make_distilled(
    project_id=None, session_id=None, learning_space_id=None,
    distilled_context="## Task Analysis\nPending context",
):
    return SkillLearnDistilled(
        project_id=project_id or uuid.uuid4(),
        session_id=session_id or uuid.uuid4(),
        task_id=uuid.uuid4(),
        learning_space_id=learning_space_id or uuid.uuid4(),
        distilled_context=distilled_context,
    )


def _setup_db_mock(mock_db, db_session=None):
    if db_session is None:
        db_session = AsyncMock()
    mock_db.get_session_context.return_value.__aenter__ = AsyncMock(
        return_value=db_session
    )
    mock_db.get_session_context.return_value.__aexit__ = AsyncMock(
        return_value=False
    )
    return db_session


# =============================================================================
# Multi-turn tool dispatch
# =============================================================================


class TestAgentMultiTurn:
    @pytest.mark.asyncio
    async def test_reads_skill_and_edits_file(self):
        """Agent multi-turn: report_thinking → get_skill → get_skill_file + str_replace + finish."""
        skill = _make_skill_info(
            name="auth-patterns",
            file_paths=["SKILL.md", "scripts/check.py"],
        )
        project_id = uuid.uuid4()
        ls_id = uuid.uuid4()
        user_id = uuid.uuid4()

        original_content = "# Auth\nAlways verify tokens."
        updated_artifact = MagicMock()

        llm_responses = [
            _llm(tool_calls=[
                _tc("report_thinking", {"thinking": "I should update auth-patterns with the new pattern."}),
            ]),
            _llm(tool_calls=[
                _tc("get_skill", {"skill_name": "auth-patterns"}),
            ]),
            _llm(tool_calls=[
                _tc("get_skill_file", {"skill_name": "auth-patterns", "file_path": "SKILL.md"}),
                _tc("str_replace_skill_file", {
                    "skill_name": "auth-patterns",
                    "file_path": "scripts/check.py",
                    "old_string": "Always verify tokens.",
                    "new_string": "Always verify tokens.\n- Check expiry before retry.",
                }),
                _tc("finish", {}),
            ]),
        ]

        mock_artifact = MagicMock()
        mock_artifact.asset_meta = {"content": "---\nname: auth-patterns\ndescription: Authentication best practices\n---\n# SKILL.md body"}

        mock_script_artifact = MagicMock()
        mock_script_artifact.asset_meta = {
            "content": original_content,
            "mime": "text/plain",
        }

        with (
            patch("acontext_core.llm.agent.skill_learner.DB_CLIENT") as mock_db,
            patch(
                "acontext_core.llm.agent.skill_learner.llm_complete",
                new_callable=AsyncMock,
                side_effect=[Result.resolve(r) for r in llm_responses],
            ),
            patch(
                "acontext_core.llm.agent.skill_learner.response_to_sendable_message",
                return_value={"role": "assistant", "content": "ok"},
            ),
            patch(
                "acontext_core.llm.tool.skill_learner_lib.get_skill_file.get_artifact_by_path",
                new_callable=AsyncMock,
                return_value=Result.resolve(mock_artifact),
            ),
            patch(
                "acontext_core.llm.tool.skill_learner_lib.str_replace_skill_file.get_artifact_by_path",
                new_callable=AsyncMock,
                return_value=Result.resolve(mock_script_artifact),
            ),
            patch(
                "acontext_core.llm.tool.skill_learner_lib.str_replace_skill_file.upload_and_build_artifact_meta",
                new_callable=AsyncMock,
                return_value=(
                    {"bucket": "b", "s3_key": "k", "etag": "e", "sha256": "s",
                     "mime": "text/plain", "size_b": 100,
                     "content": "Always verify tokens.\n- Check expiry before retry."},
                    {"__artifact_info__": {"path": "scripts/", "filename": "check.py",
                     "mime": "text/plain", "size": 100}},
                ),
            ),
            patch(
                "acontext_core.llm.tool.skill_learner_lib.str_replace_skill_file.upsert_artifact",
                new_callable=AsyncMock,
                return_value=Result.resolve(updated_artifact),
            ) as mock_upsert,
            patch(
                "acontext_core.llm.agent.skill_learner.drain_skill_learn_pending",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            _setup_db_mock(mock_db)

            result = await skill_learner_agent(
                project_id=project_id,
                learning_space_id=ls_id,
                user_id=user_id,
                skills_info=[skill],
                distilled_context="## Task Analysis (Success)\n**Goal:** Improve auth\n...",
            )

            assert result.ok()
            mock_upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_creates_new_skill(self):
        """Agent creates a brand new skill via create_skill tool."""
        project_id = uuid.uuid4()
        ls_id = uuid.uuid4()
        user_id = uuid.uuid4()

        mock_skill = MagicMock()
        mock_skill.id = uuid.uuid4()
        mock_skill.disk_id = uuid.uuid4()
        mock_skill.name = "error-handling"
        mock_skill.description = "Error handling patterns"

        mock_artifact = MagicMock()
        mock_artifact.path = "/"
        mock_artifact.filename = "SKILL.md"

        llm_responses = [
            _llm(tool_calls=[
                _tc("report_thinking", {"thinking": "No existing skill covers this. I should create one."}),
            ]),
            _llm(tool_calls=[
                _tc("create_skill", {
                    "skill_md_content": "---\nname: error-handling\ndescription: Error handling patterns\n---\n# Error Handling\n\nAlways catch specific exceptions.",
                }),
                _tc("finish", {}),
            ]),
        ]

        with (
            patch("acontext_core.llm.agent.skill_learner.DB_CLIENT") as mock_db,
            patch(
                "acontext_core.llm.agent.skill_learner.llm_complete",
                new_callable=AsyncMock,
                side_effect=[Result.resolve(r) for r in llm_responses],
            ),
            patch(
                "acontext_core.llm.agent.skill_learner.response_to_sendable_message",
                return_value={"role": "assistant", "content": "ok"},
            ),
            patch(
                "acontext_core.llm.tool.skill_learner_lib.create_skill.db_create_skill",
                new_callable=AsyncMock,
                return_value=Result.resolve(mock_skill),
            ) as mock_create,
            patch(
                "acontext_core.llm.tool.skill_learner_lib.create_skill.add_skill_to_learning_space",
                new_callable=AsyncMock,
                return_value=Result.resolve(MagicMock()),
            ),
            patch(
                "acontext_core.llm.tool.skill_learner_lib.create_skill.list_artifacts_by_path",
                new_callable=AsyncMock,
                return_value=Result.resolve([mock_artifact]),
            ),
            patch(
                "acontext_core.llm.agent.skill_learner.drain_skill_learn_pending",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            _setup_db_mock(mock_db)

            result = await skill_learner_agent(
                project_id=project_id,
                learning_space_id=ls_id,
                user_id=user_id,
                skills_info=[],
                distilled_context="## Task Analysis (Success)\n**Goal:** Handle errors\n...",
            )

            assert result.ok()
            mock_create.assert_called_once()
            assert mock_create.call_args.kwargs["user_id"] == user_id


# =============================================================================
# Context verification
# =============================================================================


class TestAgentContextInput:
    @pytest.mark.asyncio
    async def test_receives_distilled_context_not_raw(self):
        """Agent's user message contains distilled context and available skills."""
        skill = _make_skill_info()
        project_id = uuid.uuid4()
        distilled = "## Task Analysis (Success)\n**Goal:** Fix auth bug\n**Approach:** Checked token flow."

        captured_messages = []

        async def mock_llm_complete(**kwargs):
            captured_messages.append(kwargs)
            return Result.resolve(
                _llm(content="No changes needed.", tool_calls=None)
            )

        with (
            patch("acontext_core.llm.agent.skill_learner.DB_CLIENT") as mock_db,
            patch(
                "acontext_core.llm.agent.skill_learner.llm_complete",
                new_callable=AsyncMock,
                side_effect=mock_llm_complete,
            ),
            patch(
                "acontext_core.llm.agent.skill_learner.response_to_sendable_message",
                return_value={"role": "assistant", "content": "No changes needed."},
            ),
            patch(
                "acontext_core.llm.agent.skill_learner.drain_skill_learn_pending",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            _setup_db_mock(mock_db)

            await skill_learner_agent(
                project_id=project_id,
                learning_space_id=uuid.uuid4(),
                user_id=uuid.uuid4(),
                skills_info=[skill],
                distilled_context=distilled,
            )

            assert len(captured_messages) == 1
            llm_call = captured_messages[0]

            user_msg = llm_call["history_messages"][0]["content"]
            assert "## Task Analysis (Success)" in user_msg
            assert "Fix auth bug" in user_msg
            assert "Checked token flow" in user_msg
            assert "## Available Skills" in user_msg
            assert "auth-patterns" in user_msg
            assert "report_thinking" in llm_call["system_prompt"]
            assert llm_call["prompt_kwargs"] == {"prompt_id": "agent.skill_learner"}

    @pytest.mark.asyncio
    async def test_empty_skills_shows_no_skills_message(self):
        """When no skills exist, user message says '(No skills in this learning space yet)'."""
        captured_messages = []

        async def mock_llm_complete(**kwargs):
            captured_messages.append(kwargs)
            return Result.resolve(_llm(content="I'll create one.", tool_calls=None))

        with (
            patch("acontext_core.llm.agent.skill_learner.DB_CLIENT") as mock_db,
            patch(
                "acontext_core.llm.agent.skill_learner.llm_complete",
                new_callable=AsyncMock,
                side_effect=mock_llm_complete,
            ),
            patch(
                "acontext_core.llm.agent.skill_learner.response_to_sendable_message",
                return_value={"role": "assistant", "content": "ok"},
            ),
            patch(
                "acontext_core.llm.agent.skill_learner.drain_skill_learn_pending",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            _setup_db_mock(mock_db)

            await skill_learner_agent(
                project_id=uuid.uuid4(),
                learning_space_id=uuid.uuid4(),
                user_id=uuid.uuid4(),
                skills_info=[],
                distilled_context="## Task Analysis\n...",
            )

            user_msg = captured_messages[0]["history_messages"][0]["content"]
            assert "(No skills in this learning space yet)" in user_msg


# =============================================================================
# Stopping conditions
# =============================================================================


class TestAgentStoppingConditions:
    @pytest.mark.asyncio
    async def test_stops_on_no_tool_calls(self):
        """Agent stops when LLM returns no tool calls (text-only response)."""
        with (
            patch("acontext_core.llm.agent.skill_learner.DB_CLIENT") as mock_db,
            patch(
                "acontext_core.llm.agent.skill_learner.llm_complete",
                new_callable=AsyncMock,
                return_value=Result.resolve(_llm(content="Nothing to do.")),
            ),
            patch(
                "acontext_core.llm.agent.skill_learner.response_to_sendable_message",
                return_value={"role": "assistant", "content": "Nothing to do."},
            ),
            patch(
                "acontext_core.llm.agent.skill_learner.drain_skill_learn_pending",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            _setup_db_mock(mock_db)

            result = await skill_learner_agent(
                project_id=uuid.uuid4(),
                learning_space_id=uuid.uuid4(),
                user_id=uuid.uuid4(),
                skills_info=[],
                distilled_context="## Task Analysis\n...",
            )

            assert result.ok()

    @pytest.mark.asyncio
    async def test_stops_on_finish(self):
        """Agent stops when LLM returns finish tool call."""
        with (
            patch("acontext_core.llm.agent.skill_learner.DB_CLIENT") as mock_db,
            patch(
                "acontext_core.llm.agent.skill_learner.llm_complete",
                new_callable=AsyncMock,
                return_value=Result.resolve(_llm(tool_calls=[_tc("finish", {})])),
            ),
            patch(
                "acontext_core.llm.agent.skill_learner.response_to_sendable_message",
                return_value={"role": "assistant", "content": "ok"},
            ),
            patch(
                "acontext_core.llm.agent.skill_learner.drain_skill_learn_pending",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            _setup_db_mock(mock_db)

            result = await skill_learner_agent(
                project_id=uuid.uuid4(),
                learning_space_id=uuid.uuid4(),
                user_id=uuid.uuid4(),
                skills_info=[],
                distilled_context="## Task Analysis\n...",
            )

            assert result.ok()

    @pytest.mark.asyncio
    async def test_stops_at_max_iterations(self):
        """Agent stops after max_iterations even without finish."""
        call_count = 0

        async def mock_llm(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return Result.resolve(
                _llm(tool_calls=[_tc("report_thinking", {"thinking": f"Iteration {call_count}"})])
            )

        with (
            patch("acontext_core.llm.agent.skill_learner.DB_CLIENT") as mock_db,
            patch(
                "acontext_core.llm.agent.skill_learner.llm_complete",
                new_callable=AsyncMock,
                side_effect=mock_llm,
            ),
            patch(
                "acontext_core.llm.agent.skill_learner.response_to_sendable_message",
                return_value={"role": "assistant", "content": "ok"},
            ),
            patch(
                "acontext_core.llm.agent.skill_learner.drain_skill_learn_pending",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            _setup_db_mock(mock_db)

            result = await skill_learner_agent(
                project_id=uuid.uuid4(),
                learning_space_id=uuid.uuid4(),
                user_id=uuid.uuid4(),
                skills_info=[],
                distilled_context="## Task Analysis\n...",
                max_iterations=3,
            )

            assert result.ok()
            assert call_count == 3


# =============================================================================
# Error handling
# =============================================================================


class TestAgentErrorHandling:
    @pytest.mark.asyncio
    async def test_llm_error_rejects(self):
        """Agent returns Result.reject when llm_complete fails."""
        with (
            patch("acontext_core.llm.agent.skill_learner.DB_CLIENT") as mock_db,
            patch(
                "acontext_core.llm.agent.skill_learner.llm_complete",
                new_callable=AsyncMock,
                return_value=Result.reject("LLM timeout"),
            ),
            patch(
                "acontext_core.llm.agent.skill_learner.drain_skill_learn_pending",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "acontext_core.llm.agent.skill_learner.push_skill_learn_pending",
                new_callable=AsyncMock,
            ),
        ):
            _setup_db_mock(mock_db)

            result = await skill_learner_agent(
                project_id=uuid.uuid4(),
                learning_space_id=uuid.uuid4(),
                user_id=uuid.uuid4(),
                skills_info=[],
                distilled_context="## Task Analysis\n...",
            )

            assert not result.ok()

    @pytest.mark.asyncio
    async def test_unknown_tool_rejects(self):
        """Agent rejects when LLM calls an unknown tool."""
        with (
            patch("acontext_core.llm.agent.skill_learner.DB_CLIENT") as mock_db,
            patch(
                "acontext_core.llm.agent.skill_learner.llm_complete",
                new_callable=AsyncMock,
                return_value=Result.resolve(
                    _llm(tool_calls=[_tc("nonexistent_tool", {"x": 1})])
                ),
            ),
            patch(
                "acontext_core.llm.agent.skill_learner.response_to_sendable_message",
                return_value={"role": "assistant", "content": "ok"},
            ),
            patch(
                "acontext_core.llm.agent.skill_learner.drain_skill_learn_pending",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "acontext_core.llm.agent.skill_learner.push_skill_learn_pending",
                new_callable=AsyncMock,
            ),
        ):
            _setup_db_mock(mock_db)

            result = await skill_learner_agent(
                project_id=uuid.uuid4(),
                learning_space_id=uuid.uuid4(),
                user_id=uuid.uuid4(),
                skills_info=[],
                distilled_context="## Task Analysis\n...",
            )

            assert not result.ok()
            _, error = result.unpack()
            assert "not found" in error.errmsg.lower()


# =============================================================================
# State preservation across iterations
# =============================================================================


class TestAgentStatePreservation:
    @pytest.mark.asyncio
    async def test_thinking_preserved_across_iterations(self):
        """has_reported_thinking set in iter 1 allows edits in iter 2."""
        skill = _make_skill_info(name="my-skill", file_paths=["SKILL.md", "notes.md"])

        mock_artifact = MagicMock()
        mock_artifact.asset_meta = {"content": "Old content", "mime": "text/plain"}

        updated_artifact = MagicMock()

        llm_responses = [
            _llm(tool_calls=[
                _tc("report_thinking", {"thinking": "I should edit notes.md."}),
            ]),
            _llm(tool_calls=[
                _tc("str_replace_skill_file", {
                    "skill_name": "my-skill",
                    "file_path": "notes.md",
                    "old_string": "Old content",
                    "new_string": "New content",
                }),
                _tc("finish", {}),
            ]),
        ]

        with (
            patch("acontext_core.llm.agent.skill_learner.DB_CLIENT") as mock_db,
            patch(
                "acontext_core.llm.agent.skill_learner.llm_complete",
                new_callable=AsyncMock,
                side_effect=[Result.resolve(r) for r in llm_responses],
            ),
            patch(
                "acontext_core.llm.agent.skill_learner.response_to_sendable_message",
                return_value={"role": "assistant", "content": "ok"},
            ),
            patch(
                "acontext_core.llm.tool.skill_learner_lib.str_replace_skill_file.get_artifact_by_path",
                new_callable=AsyncMock,
                return_value=Result.resolve(mock_artifact),
            ),
            patch(
                "acontext_core.llm.tool.skill_learner_lib.str_replace_skill_file.upload_and_build_artifact_meta",
                new_callable=AsyncMock,
                return_value=(
                    {"bucket": "b", "s3_key": "k", "etag": "e", "sha256": "s",
                     "mime": "text/plain", "size_b": 11,
                     "content": "New content"},
                    {"__artifact_info__": {"path": "/", "filename": "notes.md",
                     "mime": "text/plain", "size": 11}},
                ),
            ) as mock_upload,
            patch(
                "acontext_core.llm.tool.skill_learner_lib.str_replace_skill_file.upsert_artifact",
                new_callable=AsyncMock,
                return_value=Result.resolve(updated_artifact),
            ) as mock_upsert,
            patch(
                "acontext_core.llm.agent.skill_learner.drain_skill_learn_pending",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            _setup_db_mock(mock_db)

            result = await skill_learner_agent(
                project_id=uuid.uuid4(),
                learning_space_id=uuid.uuid4(),
                user_id=uuid.uuid4(),
                skills_info=[skill],
                distilled_context="## Task Analysis\n...",
            )

            assert result.ok()
            mock_upsert.assert_called_once()
            upload_content = mock_upload.call_args[0][3]
            assert upload_content == "New content"

    @pytest.mark.asyncio
    async def test_tool_responses_appended_to_messages(self):
        """Tool responses are appended to conversation history for next LLM call."""
        skill = _make_skill_info()
        captured_calls = []

        async def mock_llm_complete(**kwargs):
            captured_calls.append(kwargs)
            if len(captured_calls) == 1:
                return Result.resolve(
                    _llm(tool_calls=[_tc("get_skill", {"skill_name": "auth-patterns"}, call_id="call_1")])
                )
            else:
                return Result.resolve(_llm(tool_calls=[_tc("finish", {})]))

        with (
            patch("acontext_core.llm.agent.skill_learner.DB_CLIENT") as mock_db,
            patch(
                "acontext_core.llm.agent.skill_learner.llm_complete",
                new_callable=AsyncMock,
                side_effect=mock_llm_complete,
            ),
            patch(
                "acontext_core.llm.agent.skill_learner.response_to_sendable_message",
                return_value={"role": "assistant", "content": "ok"},
            ),
            patch(
                "acontext_core.llm.agent.skill_learner.drain_skill_learn_pending",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            _setup_db_mock(mock_db)

            result = await skill_learner_agent(
                project_id=uuid.uuid4(),
                learning_space_id=uuid.uuid4(),
                user_id=uuid.uuid4(),
                skills_info=[skill],
                distilled_context="## Task Analysis\n...",
            )

            assert result.ok()
            assert len(captured_calls) == 2
            second_call_messages = captured_calls[1]["history_messages"]
            tool_msgs = [m for m in second_call_messages if m.get("role") == "tool"]
            assert len(tool_msgs) == 1
            assert tool_msgs[0]["tool_call_id"] == "call_1"
            assert "auth-patterns" in tool_msgs[0]["content"]


# =============================================================================
# Redis drain & injection tests
# =============================================================================


class TestAgentRedisDrain:
    @pytest.mark.asyncio
    async def test_drains_on_entry(self):
        """Agent drains pending contexts on entry and includes them in first user message."""
        project_id = uuid.uuid4()
        ls_id = uuid.uuid4()

        pending_ctx = _make_distilled(
            project_id=project_id,
            learning_space_id=ls_id,
            distilled_context="## Task Analysis\nPending from crash",
        )

        captured_messages = []

        async def mock_llm_complete(**kwargs):
            captured_messages.append(kwargs)
            return Result.resolve(_llm(content="Done.", tool_calls=None))

        drain_calls = [0]

        async def mock_drain(pid, lsid, **kwargs):
            drain_calls[0] += 1
            if drain_calls[0] == 1:
                return [pending_ctx]
            return []

        with (
            patch("acontext_core.llm.agent.skill_learner.DB_CLIENT") as mock_db,
            patch(
                "acontext_core.llm.agent.skill_learner.llm_complete",
                new_callable=AsyncMock,
                side_effect=mock_llm_complete,
            ),
            patch(
                "acontext_core.llm.agent.skill_learner.response_to_sendable_message",
                return_value={"role": "assistant", "content": "ok"},
            ),
            patch(
                "acontext_core.llm.agent.skill_learner.drain_skill_learn_pending",
                new_callable=AsyncMock,
                side_effect=mock_drain,
            ),
        ):
            _setup_db_mock(mock_db)

            result = await skill_learner_agent(
                project_id=project_id,
                learning_space_id=ls_id,
                user_id=uuid.uuid4(),
                skills_info=[],
                distilled_context="## Task Analysis\nInitial context",
            )

            assert result.ok()
            user_msg = captured_messages[0]["history_messages"][0]["content"]
            assert "Pending from crash" in user_msg
            assert "Initial context" in user_msg

    @pytest.mark.asyncio
    async def test_no_pending_behaves_identically(self):
        """No pending contexts → agent behaves identically to before."""
        captured_messages = []

        async def mock_llm_complete(**kwargs):
            captured_messages.append(kwargs)
            return Result.resolve(_llm(content="Done.", tool_calls=None))

        with (
            patch("acontext_core.llm.agent.skill_learner.DB_CLIENT") as mock_db,
            patch(
                "acontext_core.llm.agent.skill_learner.llm_complete",
                new_callable=AsyncMock,
                side_effect=mock_llm_complete,
            ),
            patch(
                "acontext_core.llm.agent.skill_learner.response_to_sendable_message",
                return_value={"role": "assistant", "content": "ok"},
            ),
            patch(
                "acontext_core.llm.agent.skill_learner.drain_skill_learn_pending",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            _setup_db_mock(mock_db)

            result = await skill_learner_agent(
                project_id=uuid.uuid4(),
                learning_space_id=uuid.uuid4(),
                user_id=uuid.uuid4(),
                skills_info=[],
                distilled_context="## Task Analysis\nOnly context",
            )

            assert result.ok()
            data, _ = result.unpack()
            assert data == []
            user_msg = captured_messages[0]["history_messages"][0]["content"]
            assert "Pending" not in user_msg

    @pytest.mark.asyncio
    async def test_between_iterations_injects_user_message(self):
        """Pending contexts drained between iterations are injected as user message."""
        project_id = uuid.uuid4()
        ls_id = uuid.uuid4()

        mid_run_ctx = _make_distilled(
            project_id=project_id,
            learning_space_id=ls_id,
            distilled_context="## Task Analysis\nMid-run context",
        )

        drain_call_count = [0]

        async def mock_drain(pid, lsid, **kwargs):
            drain_call_count[0] += 1
            if drain_call_count[0] == 2:
                return [mid_run_ctx]
            return []

        captured_messages = []

        async def mock_llm_complete(**kwargs):
            captured_messages.append(kwargs)
            if len(captured_messages) == 1:
                return Result.resolve(
                    _llm(tool_calls=[_tc("report_thinking", {"thinking": "Working..."})])
                )
            else:
                return Result.resolve(_llm(tool_calls=[_tc("finish", {})]))

        with (
            patch("acontext_core.llm.agent.skill_learner.DB_CLIENT") as mock_db,
            patch(
                "acontext_core.llm.agent.skill_learner.llm_complete",
                new_callable=AsyncMock,
                side_effect=mock_llm_complete,
            ),
            patch(
                "acontext_core.llm.agent.skill_learner.response_to_sendable_message",
                return_value={"role": "assistant", "content": "ok"},
            ),
            patch(
                "acontext_core.llm.agent.skill_learner.drain_skill_learn_pending",
                new_callable=AsyncMock,
                side_effect=mock_drain,
            ),
            patch(
                "acontext_core.llm.agent.skill_learner._refresh_skills",
                new_callable=AsyncMock,
                return_value={},
            ),
        ):
            _setup_db_mock(mock_db)

            result = await skill_learner_agent(
                project_id=project_id,
                learning_space_id=ls_id,
                user_id=uuid.uuid4(),
                skills_info=[],
                distilled_context="## Task Analysis\nInitial",
            )

            assert result.ok()
            second_call_msgs = captured_messages[1]["history_messages"]
            user_msgs = [m for m in second_call_msgs if m.get("role") == "user"]
            injected = [m for m in user_msgs if "Mid-run context" in m["content"]]
            assert len(injected) == 1

    @pytest.mark.asyncio
    async def test_returns_drained_session_ids_on_success(self):
        """Agent returns list of drained session IDs on success."""
        project_id = uuid.uuid4()
        ls_id = uuid.uuid4()
        pending_session_id = uuid.uuid4()

        pending = _make_distilled(
            project_id=project_id,
            session_id=pending_session_id,
            learning_space_id=ls_id,
        )

        drain_calls = [0]

        async def mock_drain(pid, lsid, **kwargs):
            drain_calls[0] += 1
            if drain_calls[0] == 1:
                return [pending]
            return []

        with (
            patch("acontext_core.llm.agent.skill_learner.DB_CLIENT") as mock_db,
            patch(
                "acontext_core.llm.agent.skill_learner.llm_complete",
                new_callable=AsyncMock,
                return_value=Result.resolve(_llm(content="Done.")),
            ),
            patch(
                "acontext_core.llm.agent.skill_learner.response_to_sendable_message",
                return_value={"role": "assistant", "content": "ok"},
            ),
            patch(
                "acontext_core.llm.agent.skill_learner.drain_skill_learn_pending",
                new_callable=AsyncMock,
                side_effect=mock_drain,
            ),
        ):
            _setup_db_mock(mock_db)

            result = await skill_learner_agent(
                project_id=project_id,
                learning_space_id=ls_id,
                user_id=uuid.uuid4(),
                skills_info=[],
                distilled_context="## Task Analysis\nInitial",
            )

            assert result.ok()
            data, _ = result.unpack()
            assert pending_session_id in data

    @pytest.mark.asyncio
    async def test_repushes_drained_on_failure(self):
        """Agent re-pushes all drained items to Redis on RuntimeError."""
        project_id = uuid.uuid4()
        ls_id = uuid.uuid4()

        pending = _make_distilled(
            project_id=project_id,
            learning_space_id=ls_id,
        )

        drain_calls = [0]

        async def mock_drain(pid, lsid, **kwargs):
            drain_calls[0] += 1
            if drain_calls[0] == 1:
                return [pending]
            return []

        with (
            patch("acontext_core.llm.agent.skill_learner.DB_CLIENT") as mock_db,
            patch(
                "acontext_core.llm.agent.skill_learner.llm_complete",
                new_callable=AsyncMock,
                return_value=Result.reject("LLM timeout"),
            ),
            patch(
                "acontext_core.llm.agent.skill_learner.drain_skill_learn_pending",
                new_callable=AsyncMock,
                side_effect=mock_drain,
            ),
            patch(
                "acontext_core.llm.agent.skill_learner.push_skill_learn_pending",
                new_callable=AsyncMock,
            ) as mock_push,
        ):
            _setup_db_mock(mock_db)

            result = await skill_learner_agent(
                project_id=project_id,
                learning_space_id=ls_id,
                user_id=uuid.uuid4(),
                skills_info=[],
                distilled_context="## Task Analysis\nInitial",
            )

            assert not result.ok()
            mock_push.assert_called_once_with(
                project_id, ls_id, pending.model_dump_json()
            )

    @pytest.mark.asyncio
    async def test_finish_overridden_when_pending(self):
        """Finish is overridden when pending contexts exist — injects and continues."""
        project_id = uuid.uuid4()
        ls_id = uuid.uuid4()

        mid_run_ctx = _make_distilled(
            project_id=project_id,
            learning_space_id=ls_id,
            distilled_context="## Task Analysis\nNew context after finish",
        )

        drain_call_count = [0]

        async def mock_drain(pid, lsid, **kwargs):
            drain_call_count[0] += 1
            if drain_call_count[0] == 2:
                return [mid_run_ctx]
            return []

        captured_messages = []

        async def mock_llm_complete(**kwargs):
            captured_messages.append(kwargs)
            if len(captured_messages) == 1:
                return Result.resolve(_llm(tool_calls=[_tc("finish", {})]))
            elif len(captured_messages) == 2:
                return Result.resolve(_llm(tool_calls=[_tc("finish", {})]))
            return Result.resolve(_llm(content="Done."))

        with (
            patch("acontext_core.llm.agent.skill_learner.DB_CLIENT") as mock_db,
            patch(
                "acontext_core.llm.agent.skill_learner.llm_complete",
                new_callable=AsyncMock,
                side_effect=mock_llm_complete,
            ),
            patch(
                "acontext_core.llm.agent.skill_learner.response_to_sendable_message",
                return_value={"role": "assistant", "content": "ok"},
            ),
            patch(
                "acontext_core.llm.agent.skill_learner.drain_skill_learn_pending",
                new_callable=AsyncMock,
                side_effect=mock_drain,
            ),
            patch(
                "acontext_core.llm.agent.skill_learner._refresh_skills",
                new_callable=AsyncMock,
                return_value={},
            ),
        ):
            _setup_db_mock(mock_db)

            result = await skill_learner_agent(
                project_id=project_id,
                learning_space_id=ls_id,
                user_id=uuid.uuid4(),
                skills_info=[],
                distilled_context="## Task Analysis\nInitial",
            )

            assert result.ok()
            assert len(captured_messages) == 2
            second_call_msgs = captured_messages[1]["history_messages"]
            user_msgs = [m for m in second_call_msgs if m.get("role") == "user"]
            injected = [m for m in user_msgs if "New context after finish" in m["content"]]
            assert len(injected) == 1

    @pytest.mark.asyncio
    async def test_finish_honored_when_no_pending(self):
        """Finish is honored when the pending list is empty."""
        with (
            patch("acontext_core.llm.agent.skill_learner.DB_CLIENT") as mock_db,
            patch(
                "acontext_core.llm.agent.skill_learner.llm_complete",
                new_callable=AsyncMock,
                return_value=Result.resolve(_llm(tool_calls=[_tc("finish", {})])),
            ),
            patch(
                "acontext_core.llm.agent.skill_learner.response_to_sendable_message",
                return_value={"role": "assistant", "content": "ok"},
            ),
            patch(
                "acontext_core.llm.agent.skill_learner.drain_skill_learn_pending",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            _setup_db_mock(mock_db)

            result = await skill_learner_agent(
                project_id=uuid.uuid4(),
                learning_space_id=uuid.uuid4(),
                user_id=uuid.uuid4(),
                skills_info=[],
                distilled_context="## Task Analysis\n...",
            )

            assert result.ok()


# =============================================================================
# Lock TTL renewal
# =============================================================================


class TestAgentLockRenewal:
    @pytest.mark.asyncio
    async def test_renews_lock_between_iterations(self):
        """Lock TTL is renewed between iterations when lock_key is provided."""
        call_count = [0]

        async def mock_llm(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] <= 2:
                return Result.resolve(
                    _llm(tool_calls=[_tc("report_thinking", {"thinking": f"Iter {call_count[0]}"})])
                )
            return Result.resolve(_llm(tool_calls=[_tc("finish", {})]))

        with (
            patch("acontext_core.llm.agent.skill_learner.DB_CLIENT") as mock_db,
            patch(
                "acontext_core.llm.agent.skill_learner.llm_complete",
                new_callable=AsyncMock,
                side_effect=mock_llm,
            ),
            patch(
                "acontext_core.llm.agent.skill_learner.response_to_sendable_message",
                return_value={"role": "assistant", "content": "ok"},
            ),
            patch(
                "acontext_core.llm.agent.skill_learner.drain_skill_learn_pending",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "acontext_core.llm.agent.skill_learner.renew_redis_lock",
                new_callable=AsyncMock,
                return_value=True,
            ) as mock_renew,
        ):
            _setup_db_mock(mock_db)

            project_id = uuid.uuid4()
            result = await skill_learner_agent(
                project_id=project_id,
                learning_space_id=uuid.uuid4(),
                user_id=uuid.uuid4(),
                skills_info=[],
                distilled_context="## Task Analysis\n...",
                lock_key="skill_learn.test",
                lock_ttl_seconds=240,
            )

            assert result.ok()
            assert mock_renew.call_count == 2
            for c in mock_renew.call_args_list:
                assert c[0][1] == "skill_learn.test"
                assert c[0][2] == 240


# =============================================================================
# Max iterations extension
# =============================================================================


class TestAgentIterationsExtension:
    EXTRA_ITERS = 3

    @pytest.mark.asyncio
    async def test_extends_max_iterations_on_new_contexts(self):
        """max_iterations increases by extra_iters when new contexts arrive."""
        project_id = uuid.uuid4()
        ls_id = uuid.uuid4()

        mid_run_ctx = _make_distilled(
            project_id=project_id,
            learning_space_id=ls_id,
        )

        drain_call_count = [0]

        async def mock_drain(pid, lsid, **kwargs):
            drain_call_count[0] += 1
            if drain_call_count[0] == 2:
                return [mid_run_ctx]
            return []

        call_count = [0]

        async def mock_llm(*args, **kwargs):
            call_count[0] += 1
            return Result.resolve(
                _llm(tool_calls=[_tc("report_thinking", {"thinking": f"Iter {call_count[0]}"})])
            )

        with (
            patch("acontext_core.llm.agent.skill_learner.DB_CLIENT") as mock_db,
            patch(
                "acontext_core.llm.agent.skill_learner.llm_complete",
                new_callable=AsyncMock,
                side_effect=mock_llm,
            ),
            patch(
                "acontext_core.llm.agent.skill_learner.response_to_sendable_message",
                return_value={"role": "assistant", "content": "ok"},
            ),
            patch(
                "acontext_core.llm.agent.skill_learner.drain_skill_learn_pending",
                new_callable=AsyncMock,
                side_effect=mock_drain,
            ),
            patch(
                "acontext_core.llm.agent.skill_learner._refresh_skills",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch.object(
                DEFAULT_CORE_CONFIG,
                "skill_learn_extra_iterations_per_context_batch",
                self.EXTRA_ITERS,
            ),
        ):
            _setup_db_mock(mock_db)

            result = await skill_learner_agent(
                project_id=project_id,
                learning_space_id=ls_id,
                user_id=uuid.uuid4(),
                skills_info=[],
                distilled_context="## Task Analysis\n...",
                max_iterations=5,
            )

            assert result.ok()
            # 5 original + 3 extra from one drain batch = 8 total
            assert call_count[0] == 5 + self.EXTRA_ITERS

    @pytest.mark.asyncio
    async def test_context_cap_stops_draining(self):
        """Draining stops after max_contexts_per_agent_run is reached."""
        project_id = uuid.uuid4()
        ls_id = uuid.uuid4()

        async def mock_drain_always(pid, lsid, **kwargs):
            return [_make_distilled(project_id=project_id, learning_space_id=ls_id)]

        call_count = [0]

        async def mock_llm(*args, **kwargs):
            call_count[0] += 1
            return Result.resolve(
                _llm(tool_calls=[_tc("report_thinking", {"thinking": f"Iter {call_count[0]}"})])
            )

        with (
            patch("acontext_core.llm.agent.skill_learner.DB_CLIENT") as mock_db,
            patch(
                "acontext_core.llm.agent.skill_learner.llm_complete",
                new_callable=AsyncMock,
                side_effect=mock_llm,
            ),
            patch(
                "acontext_core.llm.agent.skill_learner.response_to_sendable_message",
                return_value={"role": "assistant", "content": "ok"},
            ),
            patch(
                "acontext_core.llm.agent.skill_learner.drain_skill_learn_pending",
                new_callable=AsyncMock,
                side_effect=mock_drain_always,
            ) as mock_drain,
            patch(
                "acontext_core.llm.agent.skill_learner._refresh_skills",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch.object(
                DEFAULT_CORE_CONFIG,
                "skill_learn_max_contexts_per_agent_run",
                2,
            ),
            patch.object(
                DEFAULT_CORE_CONFIG,
                "skill_learn_extra_iterations_per_context_batch",
                self.EXTRA_ITERS,
            ),
        ):
            _setup_db_mock(mock_db)

            result = await skill_learner_agent(
                project_id=project_id,
                learning_space_id=ls_id,
                user_id=uuid.uuid4(),
                skills_info=[],
                distilled_context="## Task Analysis\n...",
                max_iterations=2,
            )

            assert result.ok()
            # Drain called: 1 on entry + 1 between iterations = 2 total.
            # After that, drained_items (2) >= max_contexts (2), no more drains.
            assert mock_drain.call_count == 2
            data, _ = result.unpack()
            assert len(data) == 2
