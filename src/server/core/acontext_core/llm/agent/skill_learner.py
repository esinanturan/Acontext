from typing import List, Optional
from uuid import UUID

from ...env import LOG, DEFAULT_CORE_CONFIG
from ...telemetry.log import bound_logging_vars
from ...infra.db import DB_CLIENT
from ...schema.result import Result
from ...schema.utils import asUUID
from ...schema.mq.learning import SkillLearnDistilled
from ..complete import llm_complete, response_to_sendable_message
from ..prompt.skill_learner import SkillLearnerPrompt
from ..tool.skill_learner_tools import SKILL_LEARNER_TOOLS
from ..tool.skill_learner_lib.ctx import SkillLearnerCtx
from ...util.generate_ids import track_process
from ...service.data.learning_space import SkillInfo
from ...service.data import learning_space as LS
from ...service.utils import (
    drain_skill_learn_pending,
    push_skill_learn_pending,
    renew_redis_lock,
)


def _build_available_skills_str(skills: dict[str, SkillInfo]) -> str:
    if skills:
        return "\n".join(f"- **{s.name}**: {s.description}" for s in skills.values())
    return "(No skills in this learning space yet)"


async def _refresh_skills(
    learning_space_id: asUUID,
) -> dict[str, SkillInfo]:
    """Re-fetch skills from DB so the agent sees any it just created/modified."""
    async with DB_CLIENT.get_session_context() as db_session:
        r = await LS.get_learning_space_skill_ids(db_session, learning_space_id)
        skill_ids, eil = r.unpack()
        if eil:
            LOG.warning(f"Skill Learner: failed to refresh skill IDs: {eil}")
            return {}
        r = await LS.get_skills_info(db_session, skill_ids)
        skills_info, eil = r.unpack()
        if eil:
            LOG.warning(f"Skill Learner: failed to refresh skills info: {eil}")
            return {}
    return {si.name: si for si in skills_info}


@track_process
async def skill_learner_agent(
    project_id: asUUID,
    learning_space_id: asUUID,
    user_id: Optional[asUUID],
    skills_info: List[SkillInfo],
    distilled_context: str,
    max_iterations: int = 5,
    lock_key: Optional[str] = None,
    lock_ttl_seconds: Optional[int] = None,
) -> Result[List[UUID]]:
    skills = {si.name: si for si in skills_info}
    available_skills_str = _build_available_skills_str(skills)

    drained_items: List[SkillLearnDistilled] = []
    extra_iters = DEFAULT_CORE_CONFIG.skill_learn_extra_iterations_per_context_batch
    max_contexts = DEFAULT_CORE_CONFIG.skill_learn_max_contexts_per_agent_run

    # Drain on entry — pick up leftovers from a crashed prior run + concurrent arrivals
    initial_pending = await drain_skill_learn_pending(
        project_id, learning_space_id, max_read=max_contexts
    )
    if initial_pending:
        drained_items.extend(initial_pending)
        LOG.info(
            f"Skill Learner: drained {len(initial_pending)} pending context(s) on entry"
        )

    json_tools = [tool.model_dump() for tool in SkillLearnerPrompt.tool_schema()]
    already_iterations = 0
    has_reported_thinking = False
    _user_input = SkillLearnerPrompt.pack_skill_learner_input(
        distilled_context, available_skills_str, initial_pending or None
    )
    LOG.info(f"Skill Learner Input:\n{_user_input}")
    _messages = [{"role": "user", "content": _user_input}]

    try:
        while already_iterations < max_iterations:
            r = await llm_complete(
                system_prompt=SkillLearnerPrompt.system_prompt(),
                history_messages=_messages,
                tools=json_tools,
                prompt_kwargs=SkillLearnerPrompt.prompt_kwargs(),
            )
            llm_return, eil = r.unpack()
            if eil:
                raise RuntimeError(f"LLM call failed: {eil}")
            _messages.append(response_to_sendable_message(llm_return))
            _content_preview = (llm_return.content or "")[:20]
            LOG.info(f"Skill Learner LLM Response: {_content_preview}...")
            if not llm_return.tool_calls:
                LOG.info("Skill Learner: No tool calls found, stop iterations")
                break

            use_tools = llm_return.tool_calls
            just_finish = False
            tool_response = []

            async with DB_CLIENT.get_session_context() as db_session:
                ctx = SkillLearnerCtx(
                    db_session=db_session,
                    project_id=project_id,
                    learning_space_id=learning_space_id,
                    user_id=user_id,
                    skills=skills,
                    has_reported_thinking=has_reported_thinking,
                )

                for tool_call in use_tools:
                    tool_name = tool_call.function.name
                    if tool_name == "finish":
                        just_finish = True
                        continue
                    try:
                        tool_arguments = tool_call.function.arguments
                        tool = SKILL_LEARNER_TOOLS[tool_name]
                        with bound_logging_vars(tool=tool_name):
                            r = await tool.handler(ctx, tool_arguments)
                            t, eil = r.unpack()
                            if eil:
                                raise RuntimeError(
                                    f"Tool {tool_name} rejected: {r.error}"
                                )
                        if tool_name != "report_thinking":
                            _t_preview = (t or "")[:20]
                            LOG.info(
                                f"Skill Learner Tool Call: {tool_name} -> {_t_preview}..."
                            )
                        tool_response.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": t,
                            }
                        )
                    except KeyError as e:
                        raise RuntimeError(
                            f"Tool {tool_name} not found: {str(e)}"
                        ) from e
                    except RuntimeError:
                        raise
                    except Exception as e:
                        raise RuntimeError(f"Tool {tool_name} error: {str(e)}") from e

                has_reported_thinking = ctx.has_reported_thinking

            _messages.extend(tool_response)

            remaining = max_contexts - len(drained_items)
            if remaining > 0:
                new_contexts = await drain_skill_learn_pending(
                    project_id, learning_space_id, max_read=remaining
                )
                if new_contexts:
                    drained_items.extend(new_contexts)
                    skills = await _refresh_skills(learning_space_id)
                    available_skills_str = _build_available_skills_str(skills)
                    _new_context_input = SkillLearnerPrompt.pack_incoming_contexts(
                        new_contexts, available_skills_str,
                        count_bases=len(drained_items) - len(new_contexts),
                    )
                    _messages.append(
                        {
                            "role": "user",
                            "content": _new_context_input,
                        }
                    )
                    max_iterations += extra_iters
                    just_finish = False
                    LOG.info(
                        f"Skill Learner: injected {len(new_contexts)} new context(s) between iterations"
                    )

            # Check for pending contexts BEFORE honoring finish
            if just_finish:
                LOG.info(
                    "Skill Learner: finish called, no pending contexts — stopping."
                )
                break

            already_iterations += 1

            # Renew lock TTL to prevent expiry during extended runs
            if lock_key and lock_ttl_seconds:
                await renew_redis_lock(project_id, lock_key, lock_ttl_seconds)

    except Exception as e:
        # Re-push all drained items so the next agent picks them up
        for item in drained_items:
            await push_skill_learn_pending(
                project_id, learning_space_id, item.model_dump_json()
            )
        return Result.reject(str(e))

    return Result.resolve([item.session_id for item in drained_items])
