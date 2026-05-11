"""CLI for the lab."""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from pathlib import Path
from typing import Annotated, Protocol, cast

import typer
import yaml  # type: ignore[import-untyped]

from .graph import build_graph
from .metrics import MetricsReport, metric_from_state, summarize_metrics, write_metrics
from .persistence import build_checkpointer
from .report import write_report
from .scenarios import load_scenarios
from .state import initial_state

app = typer.Typer(no_args_is_help=True)


class GraphRunner(Protocol):
    def invoke(self, state: dict[str, object], config: dict[str, object]) -> dict[str, object]: ...

    def get_state_history(
        self,
        config: dict[str, object],
        *,
        filter: dict[str, object] | None = None,
        before: dict[str, object] | None = None,
        limit: int | None = None,
    ) -> Iterator[object]: ...


def _read_dotenv(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    env_values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        env_values[key.strip()] = value.strip()
    return env_values


def _resolve_runtime_config(cfg: dict[str, object]) -> tuple[str, str | None]:
    dotenv = _read_dotenv(Path(".env"))
    checkpointer = (
        os.getenv("CHECKPOINTER") or dotenv.get("CHECKPOINTER") or cfg.get("checkpointer", "memory")
    )
    database_url = (
        os.getenv("DATABASE_URL") or dotenv.get("DATABASE_URL") or cfg.get("database_url")
    )
    resolved_database_url = database_url if isinstance(database_url, str) else None
    return str(checkpointer), resolved_database_url


def _collect_resume_evidence(graph: GraphRunner, run_config: dict[str, object]) -> bool:
    try:
        history = list(graph.get_state_history(run_config, limit=2))
    except Exception:
        return False
    return len(history) >= 1


@app.command("run-scenarios")
def run_scenarios(
    config: Annotated[Path, typer.Option("--config")],
    output: Annotated[Path, typer.Option("--output")],
) -> None:
    """Run all grading scenarios and write metrics JSON."""
    raw_cfg = yaml.safe_load(config.read_text(encoding="utf-8"))
    if not isinstance(raw_cfg, dict):
        raise typer.BadParameter("Config must be a mapping")
    cfg: dict[str, object] = raw_cfg
    scenarios_path = cfg.get("scenarios_path")
    if not isinstance(scenarios_path, str):
        raise typer.BadParameter("scenarios_path must be a string path")
    scenarios = load_scenarios(scenarios_path)
    checkpointer_kind, database_url = _resolve_runtime_config(cfg)
    checkpointer = build_checkpointer(checkpointer_kind, database_url)
    graph = cast(GraphRunner, build_graph(checkpointer=checkpointer))
    metrics = []
    resume_success = False
    for scenario in scenarios:
        state = initial_state(scenario)
        run_config: dict[str, object] = {"configurable": {"thread_id": state["thread_id"]}}
        final_state = graph.invoke(
            cast(dict[str, object], state),
            config=run_config,
        )
        metrics.append(
            metric_from_state(
                final_state,
                scenario.expected_route.value,
                scenario.requires_approval,
            )
        )
        resume_success = resume_success or _collect_resume_evidence(graph, run_config)
    report = summarize_metrics(metrics, resume_success=resume_success)
    write_metrics(report, output)
    report_path = cfg.get("report_path")
    if isinstance(report_path, str):
        write_report(report, report_path)
    typer.echo(f"Wrote metrics to {output}")


@app.command("validate-metrics")
def validate_metrics(metrics: Annotated[Path, typer.Option("--metrics")]) -> None:
    """Validate metrics JSON schema for grading."""
    payload = json.loads(metrics.read_text(encoding="utf-8"))
    report = MetricsReport.model_validate(payload)
    if report.total_scenarios < 6:
        raise typer.BadParameter("Expected at least 6 scenarios")
    typer.echo(f"Metrics valid. success_rate={report.success_rate:.2%}")


if __name__ == "__main__":
    app()
