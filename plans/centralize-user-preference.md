# Plan: Centralize User Preferences — Task-Independent Preference Submission to Skill Learning

## Features / Show case

- **Task-independent preference submission**: The task agent can now submit user preferences without tying them to a specific task. Preferences like "I prefer TypeScript" or "my email is x@y.com" are captured regardless of which task (if any) is being discussed.
- **Immediate preference learning**: Submitted preferences are published directly to the skill agent queue after the task agent loop completes — no need to wait for a task to reach `success` or `failed`. Preferences from abandoned/long-running tasks are no longer lost.
- **Bypass distillation**: Preferences skip the context distillation step entirely (there's nothing to distill — "I prefer tabs" is already a clear statement). They're formatted as a `distilled_context` string and sent straight to the skill agent, reusing the existing `SkillLearnDistilled` → skill agent pipeline.
- **Batched per turn**: Multiple preferences detected in a single task agent turn are batched into one `SkillLearnDistilled` message, minimizing lock contention and LLM calls on the skill agent.
- **Clean separation of concerns**: Distillation now focuses purely on task outcome analysis (SOPs, anti-patterns). Preference learning has its own dedicated path. The two don't interfere.
- **Synergy with triviality filter**: The triviality filter can skip tasks like "Hi, I'm John, I use Python" (`is_worth_learning: false`). But the preferences in that message ("name is John", "uses Python") are still captured by the task agent via `submit_user_preference` and learned immediately — they never depend on distillation passing.

**Before (problem):**

```
User says "I prefer dark mode, also my email is user@co.com" during a running task
  → set_task_user_preference(task_order=1, pref="prefers dark mode, email: user@co.com")
  → Stored in task.data["user_preferences"]
  → Task never finishes (user abandons session)
  → SkillLearnTask never published
  → Preference LOST forever
```

**After (solution):**

```
User says "I prefer dark mode, also my email is user@co.com" during a running task
  → submit_user_preference(pref="prefers dark mode, email: user@co.com")
  → Accumulated in TaskCtx.pending_preferences
  → End of task agent loop → format as distilled_context → publish SkillLearnDistilled
  → Skill agent receives it immediately, updates "user-general-facts" skill
  → Preference LEARNED regardless of task outcome
```

---

## Design overview

### Data flow

```
Session Messages → Task Agent (task_agent_curd)
    │
    ├── Tool: submit_user_preference("prefers TypeScript")
    │     └── ctx.pending_preferences.append("prefers TypeScript")
    │
    ├── Tool: submit_user_preference("email: user@co.com")
    │     └── ctx.pending_preferences.append("email: user@co.com")
    │
    ├── (other tools: insert_task, update_task, etc.)
    │     └── on NEED_UPDATE_CTX: drain ctx.pending_preferences → _pending_preferences
    │         (same pattern as learning_task_ids drain to prevent loss on ctx reset)
    │
    └── End of loop:
          ├── Drain learning_task_ids → publish SkillLearnTask (existing, unchanged)
          │
          └── Drain pending_preferences → format → publish SkillLearnDistilled
                    directly to skill agent queue (RK: learning.skill.agent)
                    bypassing distillation consumer entirely
```

### `SkillLearnDistilled` message for preferences

Reuses the existing `SkillLearnDistilled` schema. The `distilled_context` field is formatted as:

```markdown
## User Preferences Observed
- Prefers TypeScript over JavaScript
- Email: user@example.com
- Always use 2-space indentation
```

The `task_id` field is set to a nil UUID (`uuid.UUID(int=0)`) since no task is associated. The skill agent receives this just like any task distillation and updates the appropriate skill (e.g., `user-general-facts`).

### Preference drain on ctx reset (critical correctness detail)

When a tool in `NEED_UPDATE_CTX` runs, `USE_CTX` is set to `None`. Before that, we must drain `pending_preferences` into the loop-level `_pending_preferences` list — same pattern as `learning_task_ids`. Without this, preferences submitted before an `update_task` call in the same tool batch would be silently lost.

### Error resilience

Unlike `_pending_learning_task_ids` which are cleared on tool error (task state may be inconsistent), `_pending_preferences` are **NOT** cleared on error. Preferences are user facts ("I prefer Python") that remain true regardless of whether `insert_task` crashed. They should still be published.

### Passing `learning_space_id` through (avoid redundant DB lookup)

The message controller already resolves `learning_space_id` to check if skill learning is enabled. Instead of passing only a boolean `enable_skill_learning` and re-resolving inside the task agent, pass `learning_space_id: Optional[asUUID]` directly. The boolean is derived from `learning_space_id is not None`.

### What changes and what doesn't

| Component | Changes? | Details |
|---|---|---|
| `TaskCtx` | **Yes** | Add `pending_preferences: list[str]` field |
| `submit_user_preference` tool | **New** | New tool, replaces `set_task_user_preference` |
| `set_task_user_preference` tool | **Removed** | Replaced by `submit_user_preference` |
| `task_tools.py` | **Yes** | Swap tool registration |
| `task.py` (agent) | **Yes** | Drain `pending_preferences` on ctx reset + publish after loop; change `enable_skill_learning` to `learning_space_id` |
| `message.py` (controller) | **Yes** | Pass `learning_space_id` instead of boolean |
| `task.py` (prompt) | **Yes** | Update preference instructions (no task_order) |
| `TaskData` schema | **Yes** | Remove `user_preferences` field |
| `TaskSchema.to_string()` | **Yes** | Remove user prefs display |
| `task.py` (service/data) | **Yes** | Remove `set_user_preference_for_task()` |
| `skill_learner.py` (prompt) | **Yes** | Remove `user_preferences_observed` from distillation prompts; add "User Preferences Observed" to skill learner system prompt context description |
| `distill.py` (tools) | **Yes** | Remove `user_preferences_observed` from tool schemas |
| `skill_learner.py` (prompt) | **Yes** | Remove `user_preferences` from `pack_distillation_input` |
| `SkillLearnDistilled` MQ schema | **No** | Reused as-is (task_id = nil UUID for preference messages) |
| `process_skill_agent` consumer | **No** | Receives `SkillLearnDistilled` as before |
| `skill_learner_agent` agent loop | **No** | Processes distilled_context as before |
| `process_skill_distillation` consumer | **No** | Unchanged (preference path bypasses it) |
| Constants (EX, RK) | **No** | Reuse `learning.skill.agent` routing key |

### Lock contention consideration

If a task completes AND preferences are submitted in the same turn, two `SkillLearnDistilled` messages are published: one from distillation (via `SkillLearnTask` → distillation consumer) and one from preferences (directly). The second will hit the Redis lock and go to the retry queue — this is already handled by the existing retry/DLX mechanism. No special handling needed.

---

## TODOs

- [ ] **1. Add `pending_preferences` to `TaskCtx`** — Add `pending_preferences: list[str] = field(default_factory=list)` to the `TaskCtx` dataclass, mirroring the existing `learning_task_ids` pattern.
  - File: `src/server/core/acontext_core/llm/tool/task_lib/ctx.py`

- [ ] **2. Create `submit_user_preference` tool** — New tool file with handler that appends the preference string to `ctx.pending_preferences`. No `task_order` parameter. Description emphasizes task-independent general preferences, personal info, constraints.
  - File: `src/server/core/acontext_core/llm/tool/task_lib/submit_preference.py` (new)

- [ ] **3. Remove `set_task_user_preference` tool** — Delete the old task-bound preference tool file.
  - File: `src/server/core/acontext_core/llm/tool/task_lib/set_preference.py` (delete)

- [ ] **4. Update task tool registry** — Replace `set_task_user_preference` import/registration with `submit_user_preference`.
  - File: `src/server/core/acontext_core/llm/tool/task_tools.py`

- [ ] **5. Update task agent prompt** — Rewrite section "5. Record User Preferences" to reflect the new task-independent tool. Remove references to `task_order` and per-task preference display. Update thinking report item 6.
  - File: `src/server/core/acontext_core/llm/prompt/task.py`

- [ ] **6. Update task agent loop** — Three changes:
  - (a) Add `_pending_preferences: list[str] = []` at the loop level (mirroring `_pending_learning_task_ids`).
  - (b) In the `NEED_UPDATE_CTX` drain block, also drain `ctx.pending_preferences` into `_pending_preferences` before setting `USE_CTX = None`. This prevents preference loss when ctx is reset mid-batch.
  - (c) After the existing `_pending_learning_task_ids` publish block, add a preference publish block: if `learning_space_id is not None` and `_pending_preferences` is non-empty, format them as a `distilled_context` string, publish `SkillLearnDistilled` directly to `RK.learning_skill_agent` with nil UUID for `task_id`.
  - (d) Do NOT clear `_pending_preferences` on tool error (unlike `_pending_learning_task_ids`).
  - (e) Change parameter `enable_skill_learning: bool` to `learning_space_id: Optional[asUUID] = None`. Derive boolean from `learning_space_id is not None`.
  - File: `src/server/core/acontext_core/llm/agent/task.py`

- [ ] **7. Update message controller** — Pass `ls_session.learning_space_id` (or `None`) instead of `enable_skill_learning` boolean to `task_agent_curd`. Remove the boolean derivation.
  - File: `src/server/core/acontext_core/service/controller/message.py`

- [ ] **8. Remove `user_preferences` from `TaskData`** — Remove the `user_preferences` field from the Pydantic model. Update `TaskSchema.to_string()` to remove the user prefs display line. Old JSONB data with `user_preferences` key is safely ignored by Pydantic v2's default `extra='ignore'` behavior.
  - File: `src/server/core/acontext_core/schema/session/task.py`

- [ ] **9. Remove `set_user_preference_for_task` data function** — Delete the function that writes preferences to task data. No longer called anywhere.
  - File: `src/server/core/acontext_core/service/data/task.py`

- [ ] **10. Remove `user_preferences_observed` from distillation tools** — Remove the `user_preferences_observed` property from both `DISTILL_SUCCESS_TOOL` and `DISTILL_FAILURE_TOOL` schemas. Update `extract_distillation_result` to no longer append the `**User Preferences Observed:**` line.
  - File: `src/server/core/acontext_core/llm/tool/skill_learner_lib/distill.py`

- [ ] **11. Remove `user_preferences` from distillation prompts** — Remove `user_preferences_observed` from `success_distillation_prompt()` and `failure_distillation_prompt()`. Remove the `user_preferences` section from `pack_distillation_input()`.
  - File: `src/server/core/acontext_core/llm/prompt/skill_learner.py`

- [ ] **12. Update skill learner system prompt for preference-only context** — Add `## User Preferences Observed` as a possible input type in the "Context You Receive" section. Instruct the agent to update a user-facts/preferences skill (e.g., `user-general-facts`) with factual entries — NOT SOP/Warning format.
  - File: `src/server/core/acontext_core/llm/prompt/skill_learner.py`

- [ ] **13. Update task agent imports** — Remove `_set_task_user_preference_tool` from `NEED_UPDATE_CTX` set. Add the new tool import. The new `submit_user_preference` tool does NOT need to be in `NEED_UPDATE_CTX` since it doesn't modify task state — it only appends to `ctx.pending_preferences`.
  - File: `src/server/core/acontext_core/llm/agent/task.py`

---

## New deps

None. All changes use existing infrastructure (Pydantic, dataclasses, RabbitMQ, UUID).

---

## Test cases

- [ ] `submit_user_preference` handler appends preference string to `ctx.pending_preferences`
- [ ] `submit_user_preference` handler rejects empty/whitespace-only preference strings
- [ ] `pending_preferences` are drained from `USE_CTX` before ctx reset in `NEED_UPDATE_CTX` block (preference submitted before `update_task` in same batch is not lost)
- [ ] `task_agent_curd` drains `pending_preferences` and publishes `SkillLearnDistilled` with formatted context when `learning_space_id is not None`
- [ ] `task_agent_curd` does NOT publish preferences when `learning_space_id is None`
- [ ] `task_agent_curd` does NOT publish when no preferences were submitted (no empty message)
- [ ] `_pending_preferences` are NOT cleared on tool error (preferences survive agent errors)
- [ ] Published `SkillLearnDistilled` has nil UUID for `task_id` and correctly formatted `distilled_context`
- [ ] Multiple preferences in one turn are batched into a single `SkillLearnDistilled` message
- [ ] `pending_preferences` are accumulated correctly across multiple tool calls within one agent iteration
- [ ] `TaskData` schema no longer includes `user_preferences` field (backward compat: old data with `user_preferences` key in JSONB doesn't break deserialization — Pydantic v2 ignores extra fields by default)
- [ ] `extract_distillation_result` no longer includes `**User Preferences Observed:**` line
- [ ] `pack_distillation_input` no longer includes `- User Preferences:` section
- [ ] Skill learner agent correctly handles `## User Preferences Observed` context (updates user-facts skill, does not create SOP/Warning entries)
- [ ] Message controller passes `learning_space_id` (or `None`) to `task_agent_curd`
