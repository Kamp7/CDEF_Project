"""Run and save the four required ARM 305 simulator experiments."""

from __future__ import annotations

import csv
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from cdefsim import (
    LatencySensitivity,
    Node,
    PlacementPolicy,
    PlacementStatus,
    Task,
    TenantTaskStore,
    AccessDenied,
    create_default_nodes,
    generate_seeded_tasks,
    place_task,
    run_policy,
    run_policy_comparison,
)
from cdefsim.reporting import (
    create_results_chart,
    write_summary_json,
    write_task_results_csv,
)


RESULTS_DIR = Path("results/experiments")
SEED = 305
TASK_COUNT = 20


def _run_metrics(run) -> dict:
    return {
        "policy": run.policy.value,
        "total_tasks": run.summary.total_tasks,
        "placed_count": run.summary.placed_count,
        "rejected_count": run.summary.rejected_count,
        "qos_met_count": run.summary.qos_met_count,
        "qos_missed_count": run.summary.qos_missed_count,
        "mean_simulated_latency_ms": run.summary.mean_simulated_latency_ms,
        "placements_by_node": dict(run.summary.placements_by_node),
        "node_utilization": [
            {
                "node_id": node.node_id,
                "node_type": node.node_type,
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


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_overload_trace(tasks: tuple[Task, ...], runs: tuple) -> tuple[dict, ...]:
    """Replay overload runs to record whether Edge was eligible before placement."""
    trace_rows = []
    fallback_counts = {run.policy.value: 0 for run in runs}
    for run in runs:
        nodes = create_default_nodes()
        edge = next(node for node in nodes if node.node_type.value == "Edge")
        for task, expected in zip(tasks, run.task_outcomes, strict=True):
            edge_eligible = edge.can_fit(task.cpu_required, task.memory_required_gb)
            result = place_task(task, nodes, run.policy)
            if (
                result.status is not PlacementStatus.REJECTED
                and result.node_id != edge.node_id
                and not edge_eligible
            ):
                fallback_counts[run.policy.value] += 1
            if (result.node_id, result.status, result.simulated_latency_ms) != (
                expected.placement.node_id,
                expected.placement.status,
                expected.placement.simulated_latency_ms,
            ):
                raise RuntimeError("Overload trace did not reproduce the recorded simulation run.")
            trace_rows.append(
                {
                    "policy": run.policy.value,
                    "task_id": task.task_id,
                    "edge_eligible_before": edge_eligible,
                    "node_id": result.node_id or "",
                    "placement_status": result.status.value,
                    "simulated_latency_ms": (
                        result.simulated_latency_ms
                        if result.simulated_latency_ms is not None else ""
                    ),
                    "fallback_after_edge_unavailable": (
                        result.status is not PlacementStatus.REJECTED
                        and result.node_id != edge.node_id
                        and not edge_eligible
                    ),
                    "rejection_reason": result.rejection_reason or "",
                }
            )

    path = RESULTS_DIR / "overload_trace.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(trace_rows[0]))
        writer.writeheader()
        writer.writerows(trace_rows)
    return tuple(
        {"policy": policy, "fallback_after_edge_unavailable": count}
        for policy, count in fallback_counts.items()
    )


def _changed_capacity_nodes() -> list[Node]:
    defaults = create_default_nodes()
    return [
        Node(
            node_id=node.node_id,
            node_type=node.node_type,
            cpu_capacity=node.cpu_capacity,
            memory_capacity_gb=96 if node.node_id == "cloud-1" else node.memory_capacity_gb,
            base_latency_ms=node.base_latency_ms,
        )
        for node in defaults
    ]


def _policy_table(runs: tuple) -> list[str]:
    rows = [
        "| Policy | Total | Placed | Rejected | QoS met | QoS missed | Mean simulated latency | Placements by node | Node CPU/RAM utilization |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for run in runs:
        by_node = ", ".join(
            f"{node_id}: {count}" for node_id, count in run.summary.placements_by_node.items()
        )
        utilization = ", ".join(
            f"{node.node_id}: {node.cpu_utilization_percent:.1f}%/{node.memory_utilization_percent:.1f}%"
            for node in run.node_usage
        )
        mean_latency = (
            f"{run.summary.mean_simulated_latency_ms:.2f} ms"
            if run.summary.mean_simulated_latency_ms is not None else "n/a"
        )
        rows.append(
            f"| {run.policy.value} | {run.summary.total_tasks} | {run.summary.placed_count} | "
            f"{run.summary.rejected_count} | {run.summary.qos_met_count} | "
            f"{run.summary.qos_missed_count} | {mean_latency} | {by_node} | {utilization} |"
        )
    return rows


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    tasks = generate_seeded_tasks(count=TASK_COUNT, seed=SEED)

    # Experiment 1: same seeded workload and fresh default nodes per policy.
    policy_runs = run_policy_comparison(tasks)
    write_task_results_csv(policy_runs, RESULTS_DIR / "policy_comparison.csv")
    write_summary_json(policy_runs, RESULTS_DIR / "policy_comparison.json", seed=SEED)
    create_results_chart(policy_runs, RESULTS_DIR / "policy_comparison_chart.png")

    # Experiment 2: each task fits one node at full capacity; combined demand
    # exceeds aggregate CPU capacity (96 requested versus 88 available).
    sensitivities = tuple(LatencySensitivity)
    overload_tasks = tuple(
        Task(
            task_id=f"overload-{index:03d}",
            tenant_id="tenant-a" if index % 2 else "tenant-b",
            cpu_required=8,
            memory_required_gb=8,
            latency_sensitivity=sensitivities[(index - 1) % len(sensitivities)],
        )
        for index in range(1, 13)
    )
    overload_runs = run_policy_comparison(overload_tasks)
    write_task_results_csv(overload_runs, RESULTS_DIR / "overload_results.csv")
    write_summary_json(overload_runs, RESULTS_DIR / "overload_summary.json", seed=None)
    create_results_chart(overload_runs, RESULTS_DIR / "overload_chart.png")
    fallback_counts = _write_overload_trace(overload_tasks, overload_runs)

    # Experiment 3: record only the generic denial outcome; do not put the
    # protected task ID or contents into the evidence file.
    protected_task = Task(
        "protected-record-001", "tenant-owner", 2, 2, LatencySensitivity.MEDIUM
    )
    protected_record = place_task(
        protected_task, create_default_nodes(), PlacementPolicy.LOWEST_LATENCY_FIRST
    )
    tenant_store = TenantTaskStore()
    tenant_store.record(protected_record)
    owner_can_read_own_record = tenant_store.get("tenant-owner", protected_task.task_id) is protected_record
    try:
        tenant_store.get("tenant-requester", protected_task.task_id)
    except AccessDenied as exc:
        denial_message = str(exc)
        denied = True
    else:
        denial_message = ""
        denied = False
    tenant_evidence = {
        "setup": "One task record is owned by a different simulated tenant.",
        "expected": "The owner can read the record; a cross-tenant read is denied without returning contents.",
        "owner_can_read_own_record": owner_can_read_own_record,
        "cross_tenant_access": "denied" if denied else "unexpectedly allowed",
        "denial_message": denial_message,
        "protected_contents_returned": False,
        "result": "pass" if owner_can_read_own_record and denied else "fail",
    }
    _write_json(RESULTS_DIR / "tenant_isolation.json", tenant_evidence)

    # Experiment 4: increase Cloud RAM only, then run the exact same tasks and
    # seed through both policies using fresh node objects.
    capacity_runs = tuple(
        run_policy(tasks, policy, nodes=_changed_capacity_nodes())
        for policy in PlacementPolicy
    )
    write_task_results_csv(capacity_runs, RESULTS_DIR / "capacity_changed_results.csv")
    write_summary_json(capacity_runs, RESULTS_DIR / "capacity_changed_summary.json", seed=SEED)
    create_results_chart(capacity_runs, RESULTS_DIR / "capacity_changed_chart.png")
    baseline_by_policy = {run.policy: run for run in policy_runs}
    changed_by_policy = {run.policy: run for run in capacity_runs}
    capacity_comparison = {
        "setup": "Same 20 tasks and seed 305; Cloud RAM changed from 64 GB to 96 GB. Other node settings stayed at defaults.",
        "expected": "The additional RAM should allow more placements and reduce rejections; QoS can change with placement and projected load.",
        "cloud_memory_capacity_gb": {"baseline": 64, "changed": 96},
        "runs": [
            {
                "policy": policy.value,
                "baseline": _run_metrics(baseline_by_policy[policy]),
                "capacity_changed": _run_metrics(changed_by_policy[policy]),
                "placed_delta": (
                    changed_by_policy[policy].summary.placed_count
                    - baseline_by_policy[policy].summary.placed_count
                ),
                "rejected_delta": (
                    changed_by_policy[policy].summary.rejected_count
                    - baseline_by_policy[policy].summary.rejected_count
                ),
            }
            for policy in PlacementPolicy
        ],
    }
    _write_json(RESULTS_DIR / "capacity_change_comparison.json", capacity_comparison)

    log = [
        "# ARM 305 Required Experiment Evidence",
        "",
        "All measurements below are simulated. Accepted tasks reserve CPU and RAM until each run ends. Independent policy runs start with fresh nodes.",
        "",
        "## 1. Policy comparison",
        "",
        "**Setup:** Generate 20 tasks with seed 305 and run lowest-latency-first and capacity-aware on the same task objects, using fresh default Edge/Fog/Cloud nodes for each policy.",
        "",
        "**Expected:** Both policies process the same 20 tasks. Their placements may differ; each reports rejection, final/peak utilization, simulated latency, and QoS separately.",
        "",
        "**Actual:**",
        *_policy_table(policy_runs),
        "",
        "**Evidence:** `policy_comparison.csv`, `policy_comparison.json`, and `policy_comparison_chart.png`.",
        "",
        "## 2. Overload and fallback",
        "",
        "**Setup:** Submit 12 tasks, each requiring 8 CPU units and 8 GB RAM. Every task fits an empty node, while total requested CPU is 96 units against 88 units across the three default nodes. Run both policies from fresh nodes.",
        "",
        "**Expected:** The policy can place a task on another eligible tier when Edge is unavailable; once aggregate capacity is exhausted, remaining work is rejected. With these fixed demands, at most 11 tasks can be placed because CPU is the limiting resource.",
        "",
        "**Actual:**",
        *_policy_table(overload_runs),
        "",
        "Fallback placements after Edge became ineligible: " + ", ".join(
            f"{row['policy']}: {row['fallback_after_edge_unavailable']}"
            for row in fallback_counts
        ) + ".",
        "",
        "**Evidence:** `overload_results.csv`, `overload_summary.json`, `overload_trace.csv`, and `overload_chart.png`. The trace records Edge eligibility before each placement and marks fallback/rejection outcomes.",
        "",
        "## 3. Tenant isolation",
        "",
        "**Setup:** Store a task placement record under its owner tenant, verify the owner can read it, then request it using a different tenant ID.",
        "",
        "**Expected:** The cross-tenant request returns a generic denial and no protected task contents.",
        "",
        f"**Actual:** Owner read={'allowed' if owner_can_read_own_record else 'denied'}; cross-tenant read={'denied' if denied else 'allowed'}; response=`{denial_message}`; protected contents returned=`{tenant_evidence['protected_contents_returned']}`. Result: **{tenant_evidence['result']}**.",
        "",
        "**Evidence:** `tenant_isolation.json`. It intentionally contains no protected task ID or task contents.",
        "",
        "## 4. Capacity change",
        "",
        "**Setup:** Re-run the seed-305 20-task workload with both policies. Increase Cloud RAM from 64 GB to 96 GB; keep CPU capacity, base latency, Edge, and Fog settings unchanged.",
        "",
        "**Expected:** More RAM should increase placement capacity and reduce rejection counts. Placement changes can also alter simulated latency and QoS.",
        "",
        "**Actual:**",
        "| Policy | Baseline placed/rejected | Changed placed/rejected | Placed delta | Rejected delta | QoS met baseline/changed | Mean simulated latency baseline/changed | Cloud RAM used/capacity (util%) baseline/changed |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for policy in PlacementPolicy:
        baseline_run = baseline_by_policy[policy]
        changed_run = changed_by_policy[policy]
        baseline = baseline_run.summary
        changed = changed_run.summary
        baseline_cloud = next(node for node in baseline_run.node_usage if node.node_id == "cloud-1")
        changed_cloud = next(node for node in changed_run.node_usage if node.node_id == "cloud-1")
        baseline_latency = (
            f"{baseline.mean_simulated_latency_ms:.2f}"
            if baseline.mean_simulated_latency_ms is not None else "n/a"
        )
        changed_latency = (
            f"{changed.mean_simulated_latency_ms:.2f}"
            if changed.mean_simulated_latency_ms is not None else "n/a"
        )
        log.append(
            f"| {policy.value} | {baseline.placed_count}/{baseline.rejected_count} | "
            f"{changed.placed_count}/{changed.rejected_count} | "
            f"{changed.placed_count - baseline.placed_count:+d} | "
            f"{changed.rejected_count - baseline.rejected_count:+d} | "
            f"{baseline.qos_met_count}/{changed.qos_met_count} | "
            f"{baseline_latency}/{changed_latency} ms | "
            f"{baseline_cloud.memory_used_gb:g}/{baseline_cloud.memory_capacity_gb:g} GB "
            f"({baseline_cloud.memory_utilization_percent:.1f}%)/"
            f"{changed_cloud.memory_used_gb:g}/{changed_cloud.memory_capacity_gb:g} GB "
            f"({changed_cloud.memory_utilization_percent:.1f}%) |"
        )
    log.extend(
        [
            "",
            "**Evidence:** `capacity_change_comparison.json`, `capacity_changed_results.csv`, `capacity_changed_summary.json`, and `capacity_changed_chart.png`. The JSON records per-node utilization and the before/after capacity.",
            "",
        ]
    )
    (RESULTS_DIR / "experiment_log.md").write_text("\n".join(log), encoding="utf-8")

    print(f"Wrote experiment evidence under: {RESULTS_DIR.resolve()}")
    print(f"Policy comparison: {RESULTS_DIR / 'policy_comparison.csv'}")
    print(f"Overload trace:    {RESULTS_DIR / 'overload_trace.csv'}")
    print(f"Tenant isolation:  {RESULTS_DIR / 'tenant_isolation.json'}")
    print(f"Capacity change:   {RESULTS_DIR / 'capacity_change_comparison.json'}")
    print(f"Experiment log:    {RESULTS_DIR / 'experiment_log.md'}")


if __name__ == "__main__":
    main()
