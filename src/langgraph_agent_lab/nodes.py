"""Node skeletons for the LangGraph workflow.

Each function should be small, testable, and return a partial state update. Avoid mutating the
input state in place.
"""

from __future__ import annotations

import re

from .state import AgentState, ApprovalDecision, Route, make_event

RISKY_KEYWORDS = {"refund", "delete", "send", "cancel", "remove", "revoke"}
TOOL_KEYWORDS = {"status", "order", "lookup", "check", "track", "find", "search"}
ERROR_KEYWORDS = {"timeout", "fail", "failure", "error", "crash", "unavailable"}
VAGUE_PRONOUNS = {"it", "this", "that", "them", "thing"}


def _tokenize(query: str) -> list[str]:
    return re.findall(r"\b[a-z0-9]+\b", query.lower())


def intake_node(state: AgentState) -> dict:
    """Normalize raw query into state fields.

    TODO(student): add normalization, PII checks, and metadata extraction.
    """
    # Implement
    query = state.get("query", "").strip()
    return {
        "query": query,
        "messages": [f"intake:{query[:40]}"],
        "events": [make_event("intake", "completed", "query normalized")],
    }


def classify_node(state: AgentState) -> dict:
    """Classify the query into a route.

    TODO(student): replace keyword heuristics with a clear routing policy.
    Required routes: simple, tool, missing_info, risky, error.
    """
    # Implement
    query = str(state.get("query", ""))
    tokens = _tokenize(query)
    token_set = set(tokens)
    route = Route.SIMPLE
    risk_level = "low"
    if token_set.intersection(RISKY_KEYWORDS):
        route = Route.RISKY
        risk_level = "high"
    elif token_set.intersection(TOOL_KEYWORDS):
        route = Route.TOOL
    elif len(tokens) < 5 and token_set.intersection(VAGUE_PRONOUNS):
        route = Route.MISSING_INFO
    elif token_set.intersection(ERROR_KEYWORDS):
        route = Route.ERROR
    return {
        "route": route.value,
        "risk_level": risk_level,
        "events": [make_event("classify", "completed", f"route={route.value}")],
    }


def ask_clarification_node(state: AgentState) -> dict:
    """Ask for missing information instead of hallucinating.

    TODO(student): generate a specific clarification question from state.
    """
    # Implement
    query = str(state.get("query", "")).lower()
    if "order" in query:
        question = "Please share the order ID and the exact issue so I can continue."
    else:
        question = "Could you provide the account, request details, and expected outcome?"
    return {
        "pending_question": question,
        "final_answer": question,
        "events": [make_event("clarify", "completed", "missing information requested")],
    }


def tool_node(state: AgentState) -> dict:
    """Call a mock tool.

    Simulates transient failures for error-route scenarios to demonstrate retry loops.
    TODO(student): implement idempotent tool execution and structured tool results.
    """
    # Implement
    attempt = int(state.get("attempt", 0))
    scenario_id = state.get("scenario_id", "unknown")
    should_error = state.get("route") == Route.ERROR.value and attempt < 2
    if should_error:
        result = f"ERROR: transient failure attempt={attempt} scenario={scenario_id}"
    else:
        result = f"mock-tool-result for scenario={scenario_id}"
    return {
        "tool_results": [result],
        "events": [make_event("tool", "completed", f"tool executed attempt={attempt}")],
    }


def risky_action_node(state: AgentState) -> dict:
    """Prepare a risky action for approval.

    TODO(student): create a proposed action with evidence and risk justification.
    """
    # Implement
    query = state.get("query", "unspecified action")
    proposal = f"Proposed risky action: {query}. Requires human approval before execution."
    return {
        "proposed_action": proposal,
        "events": [make_event("risky_action", "pending_approval", "approval required")],
    }


def approval_node(state: AgentState) -> dict:
    """Human approval step with optional LangGraph interrupt().

    Set LANGGRAPH_INTERRUPT=true to use real interrupt() for HITL demos.
    Default uses mock decision so tests and CI run offline.

    TODO(student): implement reject/edit decisions and timeout escalation.
    """
    # Implement
    import os

    if os.getenv("LANGGRAPH_INTERRUPT", "").lower() == "true":
        from langgraph.types import interrupt

        value = interrupt(
            {
                "proposed_action": state.get("proposed_action"),
                "risk_level": state.get("risk_level"),
            }
        )
        if isinstance(value, dict):
            decision = ApprovalDecision(**value)
        else:
            decision = ApprovalDecision(approved=bool(value))
    else:
        decision = ApprovalDecision(approved=True, comment="mock approval for lab")
    return {
        "approval": decision.model_dump(),
        "events": [make_event("approval", "completed", f"approved={decision.approved}")],
    }


def retry_or_fallback_node(state: AgentState) -> dict:
    """Record a retry attempt or fallback decision.

    TODO(student): implement bounded retry, exponential backoff metadata, and fallback route.
    """
    # Implement
    current_attempt = int(state.get("attempt", 0))
    max_attempts = int(state.get("max_attempts", 3))
    attempt = current_attempt + 1
    exhausted = attempt >= max_attempts
    errors = [f"transient failure attempt={attempt}"]
    message = (
        "retry limit reached, fallback to dead letter" if exhausted else "retry attempt recorded"
    )
    return {
        "attempt": attempt,
        "errors": errors,
        "events": [
            make_event(
                "retry",
                "completed",
                message,
                attempt=attempt,
                max_attempts=max_attempts,
            )
        ],
    }


def answer_node(state: AgentState) -> dict:
    """Produce a final response.

    TODO(student): ground the answer in tool_results and approval where relevant.
    """
    # Implement
    route = state.get("route")
    latest_tool_result = state.get("tool_results", [])[-1] if state.get("tool_results") else None
    if latest_tool_result:
        answer = f"I found: {latest_tool_result}"
        approval = state.get("approval") or {}
        if route == Route.RISKY.value and approval.get("approved"):
            answer += " | Human approval: granted."
    else:
        answer = "This is a safe mock answer. Replace with your agent response."
    return {
        "final_answer": answer,
        "events": [make_event("answer", "completed", "answer generated")],
    }


def evaluate_node(state: AgentState) -> dict:
    """Evaluate tool results — the 'done?' check that enables retry loops.

    TODO(student): replace heuristic with LLM-as-judge or structured validation.
    """
    # Implement
    tool_results = state.get("tool_results", []) or []
    latest = tool_results[-1] if tool_results else ""
    if "error" in latest.lower():
        return {
            "evaluation_result": "needs_retry",
            "events": [
                make_event(
                    "evaluate",
                    "completed",
                    "tool result indicates failure, retry needed",
                )
            ],
        }
    return {
        "evaluation_result": "success",
        "events": [make_event("evaluate", "completed", "tool result satisfactory")],
    }


def dead_letter_node(state: AgentState) -> dict:
    """Log unresolvable failures for manual review.

    Third layer of error strategy: retry -> fallback -> dead letter.
    TODO(student): persist to dead-letter queue, alert on-call, or create support ticket.
    """
    # Implement
    return {
        "final_answer": (
            "Request could not be completed after maximum retry attempts. Logged for manual review."
        ),
        "events": [
            make_event(
                "dead_letter",
                "completed",
                f"max retries exceeded, attempt={state.get('attempt', 0)}",
            )
        ],
    }


def finalize_node(state: AgentState) -> dict:
    """Finalize the run and emit a final audit event."""
    return {"events": [make_event("finalize", "completed", "workflow finished")]}
