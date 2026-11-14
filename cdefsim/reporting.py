"""Console, CSV, JSON, and chart output for simulation runs."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable

from .engine import SimulationRun


def _format_table(headers: list[str], rows: list[list[str]]) -> str:
    widths = [len(header) for header in headers]
    for row in rows:
        for index, value in enumerate(row):
            widths[index] = max(widths[index], len(value))
    line = "-+-".join("-" * width for width in widths)
    render = lambda row: " | ".join(value.ljust(widths[i]) for i, value in enumerate(row))
    return "\n".join([render(headers), line, *(render(row) for row in rows)])


def format_console_report(runs: Iterable[SimulationRun], seed: int) -> str:
    runs = tuple(runs)
    if not runs:
        raise ValueError("At least one simulation run is required.")
    task_count = runs[0].summary.total_tasks
    lines = [
        f"Simulated seeded workload: {task_count} tasks (seed={seed})",
        "Resource model: placed tasks reserve CPU/RAM until each run ends; each policy starts fresh.",
    ]

    for run in runs:
        summary = run.summary
        mean_latency = (
            f"{summary.mean_simulated_latency_ms:.2f}"
            if summary.mean_simulated_latency_ms is not None
            else "n/a"
        )
        lines.extend(
            [
                "",
                f"=== Policy: {run.policy.value} ===",
                "QoS targets (assumptions): " + ", ".join(
                    f"{sensitivity.value} <= {target:g} ms"
                    for sensitivity, target in run.qos_targets_ms.items()
                ),
                (
                    f"Total={summary.total_tasks} | Placement successes={summary.placed_count} | "
                    f"Rejected={summary.rejected_count} | QoS met={summary.qos_met_count} | "
                    f"QoS missed={summary.qos_missed_count} | "
                    f"Mean simulated latency={mean_latency} ms"
                ),
            ]
        )
        task_rows = []
        for outcome in run.task_outcomes:
            placement = outcome.placement
            task = placement.task
            task_rows.append(
                [
                    task.task_id,
                    task.tenant_id,
                    task.latency_sensitivity.value,
                    placement.node_id or "-",
                    placement.status.value,
                    (
                        f"{placement.simulated_latency_ms:.2f}"
                        if placement.simulated_latency_ms is not None else "n/a"
                    ),
                    f"{outcome.qos_target_ms:.0f}",
                    "met" if outcome.qos_met is True else "missed" if outcome.qos_met is False else "n/a",
                ]
            )
        lines.extend(
            [
                "Per-task placement and simulated QoS:",
                _format_table(
                    ["Task", "Tenant", "Sensitivity", "Node", "Placement", "Sim latency ms", "Target ms", "QoS"],
                    task_rows,
                ),
            ]
        )
        usage_rows = [
            [
                node.node_id,
                node.node_type,
                f"{node.cpu_used:g}/{node.cpu_capacity:g}",
                f"{node.cpu_utilization_percent:.1f}%",
                f"{node.memory_used_gb:g}/{node.memory_capacity_gb:g} GB",
                f"{node.memory_utilization_percent:.1f}%",
            ]
            for node in run.node_usage
        ]
        lines.extend(
            [
                "Final resource utilization (also peak for this reservation model):",
                _format_table(
                    ["Node", "Tier", "CPU used/cap", "CPU", "RAM used/cap", "RAM"],
                    usage_rows,
                ),
            ]
        )
    return "\n".join(lines)


def write_task_results_csv(runs: Iterable[SimulationRun], path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "policy",
        "task_id",
        "tenant_id",
        "cpu_required",
        "memory_required_gb",
        "latency_sensitivity",
        "node_id",
        "placement_status",
        "simulated_latency_ms",
        "qos_target_ms",
        "qos_result",
        "projected_cpu_utilization_percent",
        "projected_memory_utilization_percent",
        "rejection_reason",
    ]
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for run in runs:
            for outcome in run.task_outcomes:
                result = outcome.placement
                task = result.task
                writer.writerow(
                    {
                        "policy": run.policy.value,
                        "task_id": task.task_id,
                        "tenant_id": task.tenant_id,
                        "cpu_required": task.cpu_required,
                        "memory_required_gb": task.memory_required_gb,
                        "latency_sensitivity": task.latency_sensitivity.value,
                        "node_id": result.node_id or "",
                        "placement_status": result.status.value,
                        "simulated_latency_ms": (
                            result.simulated_latency_ms if result.simulated_latency_ms is not None else ""
                        ),
                        "qos_target_ms": outcome.qos_target_ms,
                        "qos_result": (
                            "met" if outcome.qos_met is True
                            else "missed" if outcome.qos_met is False
                            else "not-evaluated"
                        ),
                        "projected_cpu_utilization_percent": (
                            100 * result.projected_cpu_utilization
                            if result.projected_cpu_utilization is not None else ""
                        ),
                        "projected_memory_utilization_percent": (
                            100 * result.projected_memory_utilization
                            if result.projected_memory_utilization is not None else ""
                        ),
                        "rejection_reason": result.rejection_reason or "",
                    }
                )
    return path


def write_summary_json(
    runs: Iterable[SimulationRun],
    path: str | Path,
    seed: int | None = None,
) -> Path:
    runs = tuple(runs)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "simulation_label": "All latency and utilization figures are simulated.",
        "random_seed": seed,
        "task_count": runs[0].summary.total_tasks if runs else 0,
        "resource_model": "Accepted tasks reserve CPU/RAM through the end of a run; policy runs start with fresh nodes.",
        "latency_model": "Configured base latency plus 20 ms times projected bottleneck utilization.",
        "runs": [
            {
                "policy": run.policy.value,
                "total_tasks": run.summary.total_tasks,
                "placed_count": run.summary.placed_count,
                "rejected_count": run.summary.rejected_count,
                "qos_met_count": run.summary.qos_met_count,
                "qos_missed_count": run.summary.qos_missed_count,
                "mean_simulated_latency_ms": run.summary.mean_simulated_latency_ms,
                "placements_by_node": dict(run.summary.placements_by_node),
                "qos_targets_ms_assumption": {
                    sensitivity.value: value
                    for sensitivity, value in run.qos_targets_ms.items()
                },
                "nodes": [
                    {
                        "node_id": node.node_id,
                        "node_type": node.node_type,
                        "base_latency_ms": node.base_latency_ms,
                        "cpu_used": node.cpu_used,
                        "cpu_capacity": node.cpu_capacity,
                        "cpu_utilization_percent": node.cpu_utilization_percent,
                        "memory_used_gb": node.memory_used_gb,
                        "memory_capacity_gb": node.memory_capacity_gb,
                        "memory_utilization_percent": node.memory_utilization_percent,
                    }
                    for node in run.node_usage
                ],
            }
            for run in runs
        ],
    }
    with path.open("w", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2)
        stream.write("\n")
    return path


def create_results_chart(runs: Iterable[SimulationRun], path: str | Path) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    runs = tuple(runs)
    if not runs:
        raise ValueError("At least one simulation run is required.")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(1, 3, figsize=(17, 6.5))
    policy_labels = [run.policy.value for run in runs]

    # Panel 1: accepted placements per node, with rejected tasks shown separately.
    bottoms = [0] * len(runs)
    node_ids = [node.node_id for node in runs[0].node_usage]
    palette = ["#4c78a8", "#f58518", "#54a24b", "#b279a2", "#e45756"]
    for index, node_id in enumerate(node_ids):
        counts = [run.summary.placements_by_node.get(node_id, 0) for run in runs]
        axes[0].bar(policy_labels, counts, bottom=bottoms, label=node_id, color=palette[index % len(palette)])
        bottoms = [bottoms[i] + counts[i] for i in range(len(runs))]
    rejected = [run.summary.rejected_count for run in runs]
    axes[0].bar(policy_labels, rejected, bottom=bottoms, label="Rejected", color="#9d9d9d")
    axes[0].set_title("Placement outcomes")
    axes[0].set_ylabel("Task count")
    axes[0].legend(fontsize=8)

    # Panel 2: final/peak utilization, split by CPU and RAM.
    categories = [(run, node) for run in runs for node in run.node_usage]
    x_positions = list(range(len(categories)))
    cpu_values = [node.cpu_utilization_percent for _, node in categories]
    memory_values = [node.memory_utilization_percent for _, node in categories]
    width = 0.36
    axes[1].bar([x - width / 2 for x in x_positions], cpu_values, width, label="CPU", color="#4c78a8")
    axes[1].bar([x + width / 2 for x in x_positions], memory_values, width, label="RAM", color="#f58518")
    axes[1].set_xticks(x_positions)
    axes[1].set_xticklabels(
        [f"{run.policy.value}\n{node.node_id}" for run, node in categories],
        rotation=25,
        ha="right",
        fontsize=8,
    )
    axes[1].set_ylim(0, 105)
    axes[1].set_ylabel("Utilization (%)")
    axes[1].set_title("Final/peak node utilization")
    axes[1].legend(fontsize=8)

    # Panel 3: QoS is measured only for placed tasks; rejections stay separate.
    metrics = [
        ("QoS met", [run.summary.qos_met_count for run in runs], "#54a24b"),
        ("QoS missed", [run.summary.qos_missed_count for run in runs], "#e45756"),
        ("Rejected", [run.summary.rejected_count for run in runs], "#9d9d9d"),
    ]
    group_width = 0.8 / max(1, len(metrics))
    for metric_index, (label, values, color) in enumerate(metrics):
        offsets = [
            x + (metric_index - (len(metrics) - 1) / 2) * group_width
            for x in x_positions[:len(runs)]
        ]
        axes[2].bar(offsets, values, group_width, label=label, color=color)
    axes[2].set_xticks(x_positions[:len(runs)])
    axes[2].set_xticklabels(policy_labels, rotation=15, ha="right", fontsize=8)
    axes[2].set_ylabel("Task count")
    axes[2].set_title("QoS and rejection totals")
    axes[2].legend(fontsize=8)

    task_count = runs[0].summary.total_tasks
    fig.suptitle(f"Simulated placement, utilization, and QoS ({task_count} tasks)", fontsize=14)
    fig.text(
        0.5,
        0.01,
        "Latency and resource use are simulated. Rejected tasks have no QoS result.",
        ha="center",
        fontsize=9,
    )
    fig.tight_layout(rect=(0, 0.04, 1, 0.92))
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path
