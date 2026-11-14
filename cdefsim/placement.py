"""Deterministic task placement policies for simulated nodes."""

from __future__ import annotations

from collections.abc import Iterable

from .models import (
    Node,
    PlacementPolicy,
    PlacementResult,
    PlacementStatus,
    Task,
)


# This is a documented simulation assumption, not a real network measurement.
LOAD_PENALTY_MS_AT_FULL_UTILIZATION = 20.0


def _stable_node_key(node: Node) -> tuple[str, str]:
    return node.node_id.casefold(), node.node_id


def _validate_node_set(nodes: Iterable[Node]) -> list[Node]:
    node_list = list(nodes)
    if not node_list:
        raise ValueError("At least one node is required.")
    if any(not isinstance(node, Node) for node in node_list):
        raise TypeError("nodes must contain Node instances.")
    ids = [node.node_id for node in node_list]
    if len(ids) != len(set(ids)):
        raise ValueError("Node IDs must be unique.")
    return node_list


def place_task(
    task: Task,
    nodes: Iterable[Node],
    policy: PlacementPolicy | str,
) -> PlacementResult:
    """Place and reserve one task, or return a rejection without changing nodes.

    Lowest-latency-first minimizes projected latency. Capacity-aware minimizes
    projected bottleneck utilization and uses projected latency as its first
    tie-breaker. Both use the node ID as the final stable tie-breaker.
    """
    if not isinstance(task, Task):
        raise TypeError("task must be a Task instance.")
    try:
        selected_policy = PlacementPolicy(policy)
    except ValueError as exc:
        raise ValueError("Unknown placement policy.") from exc

    node_list = _validate_node_set(nodes)

    # A workload item must fit at least one node at full capacity. If it does,
    # a later no-fit result is a legitimate overload rejection.
    fits_any_total_capacity = any(
        task.cpu_required <= node.cpu_capacity
        and task.memory_required_gb <= node.memory_capacity_gb
        for node in node_list
    )
    if not fits_any_total_capacity:
        raise ValueError("The task exceeds every node's total capacity.")

    eligible = [
        node for node in node_list
        if node.can_fit(task.cpu_required, task.memory_required_gb)
    ]
    if not eligible:
        return PlacementResult(
            task=task,
            policy=selected_policy,
            status=PlacementStatus.REJECTED,
            node_id=None,
            simulated_latency_ms=None,
            projected_cpu_utilization=None,
            projected_memory_utilization=None,
            rejection_reason="No node has enough remaining CPU and memory.",
        )

    def projected_values(node: Node) -> tuple[float, float, float]:
        projected_cpu, projected_memory = node.projected_utilizations(
            task.cpu_required, task.memory_required_gb
        )
        bottleneck = max(projected_cpu, projected_memory)
        latency = node.base_latency_ms + LOAD_PENALTY_MS_AT_FULL_UTILIZATION * bottleneck
        return projected_cpu, projected_memory, latency

    if selected_policy is PlacementPolicy.LOWEST_LATENCY_FIRST:
        chosen = min(
            eligible,
            key=lambda node: (projected_values(node)[2], *_stable_node_key(node)),
        )
    else:
        chosen = min(
            eligible,
            key=lambda node: (
                max(projected_values(node)[0], projected_values(node)[1]),
                projected_values(node)[2],
                *_stable_node_key(node),
            ),
        )

    cpu_util, memory_util, latency = projected_values(chosen)
    chosen.reserve(task.cpu_required, task.memory_required_gb)
    return PlacementResult(
        task=task,
        policy=selected_policy,
        status=PlacementStatus.PLACED,
        node_id=chosen.node_id,
        simulated_latency_ms=latency,
        projected_cpu_utilization=cpu_util,
        projected_memory_utilization=memory_util,
    )
