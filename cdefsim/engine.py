"""Workload execution and simulated QoS/resource summaries."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
import math
from types import MappingProxyType

from .models import (
    LatencySensitivity,
    Node,
    PlacementPolicy,
    PlacementResult,
    PlacementStatus,
    Task,
    create_default_nodes,
)
from .placement import place_task


DEFAULT_QOS_TARGETS_MS: Mapping[LatencySensitivity, float] = MappingProxyType(
    {
        LatencySensitivity.HIGH: 25.0,
        LatencySensitivity.MEDIUM: 60.0,
        LatencySensitivity.LOW: 100.0,
    }
)


@dataclass(frozen=True)
class TaskOutcome:
    placement: PlacementResult
    qos_target_ms: float
    qos_met: bool | None


@dataclass(frozen=True)
class NodeUsage:
    node_id: str
    node_type: str
    base_latency_ms: float
    cpu_used: float
    cpu_capacity: float
    cpu_utilization_percent: float
    memory_used_gb: float
    memory_capacity_gb: float
    memory_utilization_percent: float


@dataclass(frozen=True)
class RunSummary:
    policy: PlacementPolicy
    total_tasks: int
    placed_count: int
    rejected_count: int
    qos_met_count: int
    qos_missed_count: int
    mean_simulated_latency_ms: float | None
    placements_by_node: Mapping[str, int]


@dataclass(frozen=True)
class SimulationRun:
    policy: PlacementPolicy
    task_outcomes: tuple[TaskOutcome, ...]
    node_usage: tuple[NodeUsage, ...]
    summary: RunSummary
    qos_targets_ms: Mapping[LatencySensitivity, float]


def _normalize_targets(
    targets_ms: Mapping[LatencySensitivity | str, float] | None,
) -> dict[LatencySensitivity, float]:
    source = DEFAULT_QOS_TARGETS_MS if targets_ms is None else targets_ms
    normalized: dict[LatencySensitivity, float] = {}
    for sensitivity, value in source.items():
        try:
            level = LatencySensitivity(sensitivity)
        except ValueError as exc:
            raise ValueError("QoS targets must use low, medium, and high sensitivity.") from exc
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value <= 0
        ):
            raise ValueError("QoS latency targets must be positive finite numbers.")
        normalized[level] = float(value)
    missing = set(LatencySensitivity) - set(normalized)
    if missing:
        raise ValueError("A QoS target is required for low, medium, and high sensitivity.")
    return normalized


def run_policy(
    tasks: Iterable[Task],
    policy: PlacementPolicy | str,
    nodes: Iterable[Node] | None = None,
    qos_targets_ms: Mapping[LatencySensitivity | str, float] | None = None,
) -> SimulationRun:
    """Run one policy, reserving accepted tasks through the end of the run."""
    try:
        selected_policy = PlacementPolicy(policy)
    except ValueError as exc:
        raise ValueError("Unknown placement policy.") from exc

    workload = tuple(tasks)
    if not workload:
        raise ValueError("At least one task is required.")
    if any(not isinstance(task, Task) for task in workload):
        raise TypeError("tasks must contain Task instances.")
    task_ids = [task.task_id for task in workload]
    if len(task_ids) != len(set(task_ids)):
        raise ValueError("Task IDs must be unique within a workload.")

    node_list = create_default_nodes() if nodes is None else list(nodes)
    targets = _normalize_targets(qos_targets_ms)
    outcomes: list[TaskOutcome] = []
    for task in workload:
        result = place_task(task, node_list, selected_policy)
        target = targets[task.latency_sensitivity]
        qos_met = (
            result.simulated_latency_ms <= target
            if result.status is PlacementStatus.PLACED
            else None
        )
        outcomes.append(TaskOutcome(result, target, qos_met))

    node_usage = tuple(
        NodeUsage(
            node_id=node.node_id,
            node_type=node.node_type.value,
            base_latency_ms=node.base_latency_ms,
            cpu_used=node.reserved_cpu,
            cpu_capacity=node.cpu_capacity,
            cpu_utilization_percent=100 * node.cpu_utilization,
            memory_used_gb=node.reserved_memory_gb,
            memory_capacity_gb=node.memory_capacity_gb,
            memory_utilization_percent=100 * node.memory_utilization,
        )
        for node in node_list
    )

    placed_outcomes = [
        outcome for outcome in outcomes
        if outcome.placement.status is PlacementStatus.PLACED
    ]
    rejected_count = len(outcomes) - len(placed_outcomes)
    placements_by_node = {node.node_id: 0 for node in node_list}
    for outcome in placed_outcomes:
        assert outcome.placement.node_id is not None
        placements_by_node[outcome.placement.node_id] += 1
    latencies = [
        outcome.placement.simulated_latency_ms
        for outcome in placed_outcomes
        if outcome.placement.simulated_latency_ms is not None
    ]
    summary = RunSummary(
        policy=selected_policy,
        total_tasks=len(outcomes),
        placed_count=len(placed_outcomes),
        rejected_count=rejected_count,
        qos_met_count=sum(outcome.qos_met is True for outcome in outcomes),
        qos_missed_count=sum(outcome.qos_met is False for outcome in outcomes),
        mean_simulated_latency_ms=(sum(latencies) / len(latencies)) if latencies else None,
        placements_by_node=placements_by_node,
    )
    return SimulationRun(
        selected_policy,
        tuple(outcomes),
        node_usage,
        summary,
        MappingProxyType(targets),
    )


def run_policy_comparison(
    tasks: Iterable[Task],
    qos_targets_ms: Mapping[LatencySensitivity | str, float] | None = None,
) -> tuple[SimulationRun, ...]:
    """Run both policies on the same tasks with fresh, identical nodes."""
    workload = tuple(tasks)
    return tuple(
        run_policy(workload, policy, qos_targets_ms=qos_targets_ms)
        for policy in PlacementPolicy
    )
