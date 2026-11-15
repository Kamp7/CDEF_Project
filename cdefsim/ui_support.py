"""Small, UI-independent helpers for configured nodes and live task rows."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .engine import TaskOutcome
from .models import Node, NodeType


def create_configured_nodes(settings: Mapping[str, Mapping[str, float]]) -> list[Node]:
    """Build a fresh Edge/Fog/Cloud pool from UI-provided capacity settings."""
    nodes: list[Node] = []
    for node_type, key in (
        (NodeType.EDGE, "edge"),
        (NodeType.FOG, "fog"),
        (NodeType.CLOUD, "cloud"),
    ):
        if key not in settings:
            raise ValueError(f"Missing settings for the {node_type.value} node.")
        values = settings[key]
        try:
            nodes.append(
                Node(
                    node_id=f"{key}-1",
                    node_type=node_type,
                    cpu_capacity=values["cpu_capacity"],
                    memory_capacity_gb=values["memory_capacity_gb"],
                    base_latency_ms=values["base_latency_ms"],
                )
            )
        except KeyError as exc:
            raise ValueError(f"Incomplete settings for the {node_type.value} node.") from exc
    return nodes


def task_outcome_to_row(outcome: TaskOutcome) -> dict[str, Any]:
    """Convert a completed task into the columns shown in the live UI table."""
    placement = outcome.placement
    task = placement.task
    return {
        "Policy": placement.policy.value,
        "Task": task.task_id,
        "Tenant ID": task.tenant_id,
        "Sensitivity": task.latency_sensitivity.value,
        "Node": placement.node_id or "—",
        "Placement": "Placed" if placement.status.value == "placed" else "Rejected",
        "Simulated latency": (
            f"{placement.simulated_latency_ms:.2f} ms"
            if placement.simulated_latency_ms is not None
            else "—"
        ),
        "QoS": (
            "Met" if outcome.qos_met is True
            else "Miss" if outcome.qos_met is False
            else "Not evaluated"
        ),
        "QoS target": f"{outcome.qos_target_ms:.0f} ms",
    }
