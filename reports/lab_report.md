# Day 08 Lab Report

## 1. Team / student

- Name: Le Nguyen Chi Bao
- Repo/commit: local working tree
- Date: 2026-05-11

## 2. Architecture

Graph flow: `START -> intake -> classify` with conditional routes to
`answer`, `tool`, `clarify`, `risky_action`, and retry loop nodes.
The retry loop is `tool -> evaluate -> retry -> tool` and is bounded by
`max_attempts`; exhausted retries route to `dead_letter -> finalize -> END`.
Risky requests are gated by `approval` before tool execution.

## 3. State schema

| Field | Reducer | Why |
|---|---|---|
| messages | append | Keep an audit trail of key messages |
| tool_results | append | Preserve evidence across retries |
| errors | append | Keep retry/failure history |
| events | append | Trace node execution order |
| route/risk/attempt/answer/question/approval/eval | overwrite | Keep latest decision/status only |

## 4. Scenario results

| Scenario | Expected route | Actual route | Success | Retries | Interrupts |
|---|---|---|---:|---:|---:|
| S01_simple | simple | simple | yes | 0 | 0 |
| S02_tool | tool | tool | yes | 0 | 0 |
| S03_missing | missing_info | missing_info | yes | 0 | 0 |
| S04_risky | risky | risky | yes | 0 | 3 |
| S05_error | error | error | yes | 9 | 0 |
| S06_delete | risky | risky | yes | 0 | 3 |
| S07_dead_letter | error | error | yes | 3 | 0 |

### Metrics summary

- Total scenarios: 7
- Success rate: 100.00%
- Average nodes visited: 19.71
- Total retries: 12
- Total interrupts: 6
- Resume/state-history evidence: True

## 5. Failure analysis

1. Retry/tool failure: transient tool failures are detected in `evaluate`;
failed outputs set `evaluation_result=needs_retry`.
2. Risky action without approval: risky route must pass through `approval`;
non-approved outcomes route to `clarify` instead of executing tool actions.

## 6. Persistence / recovery evidence

Thread IDs are deterministic (`thread-<scenario_id>`) and passed via graph run config.
When a checkpointer is enabled, state history can be retrieved from
`get_state_history`, and `resume_success` is set from this evidence.

## 7. Extension work

Implemented checkpointer adapters for memory/sqlite/postgres with correct APIs
for current LangGraph versions.
Postgres path performs checkpointer `setup()` and supports persistent checkpoints across runs.

## 8. Improvement plan

1. Replace heuristic classifier/evaluator with structured LLM judges.
2. Add true HITL reject/edit flows with timeout escalation and operator UI.
3. Add richer latency metrics and alerting for dead-letter scenarios.

## TODO(student)

Additional evidence to attach before final submission: screenshot/log for
Postgres checkpoint table growth and one `get_state_history()` dump.
