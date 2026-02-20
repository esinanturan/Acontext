# Plan: Learning Triviality Filter — Abort Non-Worth-Learning Tasks at Distillation

## Features / Show case

- **LLM-assessed triviality gate at distillation**: The distillation LLM call (which already has full task context) now also decides whether the task is worth learning from. If it judges the task trivial, the pipeline aborts immediately — the expensive multi-iteration skill agent never runs.
- **Zero additional LLM calls**: The triviality assessment piggybacks on the existing distillation tool call by adding a `is_worth_learning` boolean + `skip_reason` string to the distillation tool schemas. No new prompts, no new LLM roundtrips.
- **Clean abort path**: `process_context_distillation` already returns `None` to signal "skip" (e.g. when task status is neither success nor failed). The consumer already handles `None` by logging and returning. We reuse this same code path.
- **Observable filtering**: When a task is skipped, a clear log line is emitted with the LLM's `skip_reason`, making it easy to audit or debug the filtering behavior.

**Examples of tasks that should be filtered out:**

| Trivial task | Why it's not worth learning |
|---|---|
| "What time is it?" | Simple factual lookup, no procedure or decision |
| "Hi" / "Hello" / small talk | Conversational, no task was actually performed |
| "Convert 5km to miles" | One-shot calculation, no reusable pattern |
| "Summarize this paragraph" | Generic capability, not a domain-specific skill |
| "What's the status of task 3?" | System query, no approach or decision involved |

**Examples of tasks that should pass through:**

| Non-trivial task | Why it's worth learning |
|---|---|
| "Deploy the API to staging" | Multi-step procedure with decisions |
| "Fix the 401 auth error on /users" | Debugging pattern, root cause analysis |
| "Set up CI/CD with GitHub Actions" | Reusable SOP |
| "Migrate the database to v2 schema" | Complex process with potential pitfalls |

---

## Design overview

### Where the filter lives

```
Task Agent marks task success/failed
  → MQ: SkillLearnTask
  → Consumer 1: process_skill_distillation
    → Controller: process_context_distillation
      → Fetch task + messages
      → LLM distillation call  ← ADDS is_worth_learning here
      → extract_distillation_result
      → ★ NEW: if not worth learning → return None (abort)
      → return SkillLearnDistilled
    → publish to skill agent queue
  → Consumer 2: process_skill_agent  ← NEVER REACHED for trivial tasks
```

The filter is added **inside the existing distillation LLM call**, not as a separate step. The `extract_distillation_result` function checks `is_worth_learning` and returns `None` (via the controller) to abort the pipeline.

### Changes to distillation tool schemas

Both `report_success_analysis` and `report_failure_analysis` get two new fields:

```python
"is_worth_learning": {
    "type": "boolean",
    "description": "Whether this task produced meaningful, reusable knowledge worth recording as a skill. Set false for trivial tasks (simple lookups, small talk, one-shot calculations, generic Q&A with no real procedure or decision)."
},
"skip_reason": {
    "type": "string",
    "description": "If is_worth_learning is false, briefly explain why (e.g. 'simple factual lookup', 'no procedure involved'). Omit if is_worth_learning is true."
}
```

- `is_worth_learning` is **required** so the LLM must always make the decision.
- `skip_reason` is **optional** (only needed when skipping) for logging/observability.

### Changes to distillation prompts

The `success_distillation_prompt` and `failure_distillation_prompt` are updated to instruct the LLM to assess triviality. A brief criteria section is appended:

```
Assess whether this task is worth learning from:
- Worth learning: tasks involving multi-step procedures, meaningful decisions, debugging, configuration, domain-specific knowledge, or user preferences.
- NOT worth learning: simple factual lookups, small talk, one-shot calculations, generic Q&A, trivial status checks, or tasks where no real procedure or decision was involved.

Set is_worth_learning accordingly. If false, provide a brief skip_reason.
```

### Changes to extraction logic

`extract_distillation_result` returns a richer result. Two options:

**Option chosen**: Return a `DistillationOutcome` dataclass containing `is_worth_learning`, `skip_reason`, and `distilled_text`. The controller checks `is_worth_learning` and returns `None` to abort.

### No changes needed to

- `SkillLearnDistilled` MQ schema (trivial tasks never reach this point)
- `process_skill_agent` consumer (never sees trivial tasks)
- `skill_learner_agent` agent loop
- Skill learner prompts or tools
- Task agent / update_task handler

---

## TODOs

- [x] **1. Update distillation tool schemas** — add `is_worth_learning` (required) and `skip_reason` (optional) to both `DISTILL_SUCCESS_TOOL` and `DISTILL_FAILURE_TOOL`
  - File: `src/server/core/acontext_core/llm/tool/skill_learner_lib/distill.py`

- [x] **2. Update `extract_distillation_result`** — parse `is_worth_learning` and `skip_reason` from tool call args, return a `DistillationOutcome` dataclass instead of raw `str`
  - File: `src/server/core/acontext_core/llm/tool/skill_learner_lib/distill.py`

- [x] **3. Update distillation prompts** — append triviality assessment instructions to `success_distillation_prompt()` and `failure_distillation_prompt()`
  - File: `src/server/core/acontext_core/llm/prompt/skill_learner.py`

- [x] **4. Update controller to check `is_worth_learning`** — after extraction, if `outcome.is_worth_learning` is `False`, log the `skip_reason` and return `Result.resolve(None)` to abort
  - File: `src/server/core/acontext_core/service/controller/skill_learner.py`

- [x] **5. Verify consumer handles `None` correctly** — confirm that `process_skill_distillation` already handles `distilled_payload is None` gracefully (it does — lines 61-65 of `service/skill_learner.py`). Update the log message to distinguish "not success/failed" from "trivial task skipped".
  - File: `src/server/core/acontext_core/service/skill_learner.py`

---

## New deps

None. All changes use existing infrastructure (Pydantic, dataclasses, standard library).

---

## Test cases

- [x] `extract_distillation_result` returns `is_worth_learning=False` + `skip_reason` when the LLM tool call sets `is_worth_learning: false`
- [x] `extract_distillation_result` returns `is_worth_learning=True` with `distilled_text` when the LLM tool call sets `is_worth_learning: true`
- [x] `extract_distillation_result` defaults to `is_worth_learning=True` if the field is somehow missing (fail-open: don't accidentally drop real learnings)
- [x] `process_context_distillation` returns `Result.resolve(None)` when distillation says not worth learning
- [x] `process_context_distillation` returns `SkillLearnDistilled` when distillation says worth learning
- [x] `process_skill_distillation` consumer logs the correct skip reason and does not publish to the skill agent queue when `None` is returned
