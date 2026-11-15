"""Browser UI for the local, simulated Edge/Fog/Cloud task placement project."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import queue
import threading
import time
from typing import Any
import uuid

import streamlit as st

from cdefsim import PlacementPolicy, SimulationRun, TaskOutcome, generate_seeded_tasks, run_policy
from cdefsim.reporting import create_results_chart, write_summary_json, write_task_results_csv
from cdefsim.ui_support import create_configured_nodes, task_outcome_to_row


PROJECT_ROOT = Path(__file__).resolve().parent
UI_RESULTS_ROOT = PROJECT_ROOT / "results" / "ui_runs"
POLICY_OPTIONS = {
    "Compare both policies": tuple(PlacementPolicy),
    "Lowest-latency-first": (PlacementPolicy.LOWEST_LATENCY_FIRST,),
    "Capacity-aware": (PlacementPolicy.CAPACITY_AWARE,),
}
NODE_LABELS = {"edge": "Edge", "fog": "Fog", "cloud": "Cloud"}


def _save_run_files(runs: tuple[SimulationRun, ...], seed: int) -> dict[str, Path]:
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f") + "_" + uuid.uuid4().hex[:6]
    output_dir = UI_RESULTS_ROOT / f"run_{run_id}"
    output_dir.mkdir(parents=True, exist_ok=False)
    csv_path = write_task_results_csv(runs, output_dir / "task_results.csv")
    json_path = write_summary_json(runs, output_dir / "run_summary.json", seed=seed)
    chart_path = create_results_chart(runs, output_dir / "placement_utilization_qos.png")
    return {"csv": csv_path, "json": json_path, "chart": chart_path}


def _run_in_background(
    tasks: tuple[Any, ...],
    policies: tuple[PlacementPolicy, ...],
    node_settings: dict[str, dict[str, float]],
    delay_seconds: float,
    event_queue: queue.Queue[tuple[str, Any]],
) -> None:
    """Run simulator policies off the UI thread and stream completed outcomes."""
    try:
        runs: list[SimulationRun] = []
        for policy in policies:
            nodes = create_configured_nodes(node_settings)

            def publish(outcome: TaskOutcome) -> None:
                event_queue.put(("task", outcome))
                if delay_seconds:
                    time.sleep(delay_seconds)

            runs.append(run_policy(tasks, policy, nodes=nodes, on_task_complete=publish))
        event_queue.put(("complete", tuple(runs)))
    except Exception as exc:
        event_queue.put(("error", str(exc)))


def _render_progress_summary(
    placeholder: Any,
    counters: dict[str, dict[str, Any]],
    selected_policies: tuple[PlacementPolicy, ...],
    task_count: int,
) -> None:
    with placeholder.container():
        columns = st.columns(len(selected_policies))
        for column, policy in zip(columns, selected_policies):
            values = counters[policy.value]
            with column:
                st.markdown(f"**{policy.value}**")
                metrics = st.columns(4)
                metrics[0].metric("Tasks", f"{values['done']}/{task_count}")
                metrics[1].metric("Placed", values["placed"])
                metrics[2].metric("Rejected", values["rejected"])
                metrics[3].metric("QoS met / miss", f"{values['met']} / {values['missed']}")
                mean_latency = (
                    sum(values["latencies"]) / len(values["latencies"])
                    if values["latencies"] else None
                )
                st.caption(
                    "Mean simulated latency so far: "
                    + (f"{mean_latency:.2f} ms" if mean_latency is not None else "—")
                )


def _update_counters(counters: dict[str, dict[str, Any]], outcome: TaskOutcome) -> None:
    policy = outcome.placement.policy.value
    values = counters[policy]
    values["done"] += 1
    if outcome.placement.status.value == "placed":
        values["placed"] += 1
        if outcome.placement.simulated_latency_ms is not None:
            values["latencies"].append(outcome.placement.simulated_latency_ms)
        if outcome.qos_met is True:
            values["met"] += 1
        elif outcome.qos_met is False:
            values["missed"] += 1
    else:
        values["rejected"] += 1


def _render_completed_results(
    runs: tuple[SimulationRun, ...],
    seed: int,
    task_count: int,
    output_paths: dict[str, Path] | None,
) -> None:
    st.subheader("Run totals")
    for run in runs:
        summary = run.summary
        st.markdown(f"#### {run.policy.value}")
        metrics = st.columns(6)
        metrics[0].metric("Tasks", summary.total_tasks)
        metrics[1].metric("Placed", summary.placed_count)
        metrics[2].metric("Rejected", summary.rejected_count)
        metrics[3].metric("QoS met", summary.qos_met_count)
        metrics[4].metric("QoS miss", summary.qos_missed_count)
        metrics[5].metric(
            "Mean latency",
            f"{summary.mean_simulated_latency_ms:.2f} ms"
            if summary.mean_simulated_latency_ms is not None else "—",
        )
        st.caption(
            "Placement by node: "
            + " · ".join(f"{node_id}: {count}" for node_id, count in summary.placements_by_node.items())
            + "  |  QoS misses are counted only for placed tasks."
        )

    all_rows = [
        task_outcome_to_row(outcome)
        for run in runs
        for outcome in run.task_outcomes
    ]
    st.subheader("Per-task results")
    st.dataframe(all_rows, hide_index=True, width="stretch")

    utilization_rows = []
    for run in runs:
        for node in run.node_usage:
            utilization_rows.append({
                "Policy": run.policy.value,
                "Node": node.node_id,
                "Tier": node.node_type,
                "CPU used / capacity": f"{node.cpu_used:g} / {node.cpu_capacity:g}",
                "CPU utilization": f"{node.cpu_utilization_percent:.1f}%",
                "RAM used / capacity (GB)": f"{node.memory_used_gb:g} / {node.memory_capacity_gb:g}",
                "RAM utilization": f"{node.memory_utilization_percent:.1f}%",
                "Base latency": f"{node.base_latency_ms:g} ms",
            })
    with st.expander("Node utilization and configured latency", expanded=False):
        st.dataframe(utilization_rows, hide_index=True, width="stretch")

    if output_paths:
        st.subheader("Saved run evidence")
        st.caption(f"Saved under `{output_paths['csv'].parent.relative_to(PROJECT_ROOT)}`")
        downloads = st.columns(3)
        downloads[0].download_button(
            "Download task CSV",
            data=output_paths["csv"].read_bytes(),
            file_name=f"task_results_seed_{seed}_{task_count}.csv",
            mime="text/csv",
        )
        downloads[1].download_button(
            "Download summary JSON",
            data=output_paths["json"].read_bytes(),
            file_name=f"run_summary_seed_{seed}_{task_count}.json",
            mime="application/json",
        )
        downloads[2].download_button(
            "Download chart PNG",
            data=output_paths["chart"].read_bytes(),
            file_name=f"placement_utilization_qos_seed_{seed}_{task_count}.png",
            mime="image/png",
        )
        st.image(str(output_paths["chart"]), caption="Simulated placement, utilization and QoS")


st.set_page_config(page_title="ARM 305 Task Placement Simulator", page_icon="☁️", layout="wide")
st.markdown(
    """
    <style>
      .block-container {padding-top: 1.7rem; padding-bottom: 2.5rem; max-width: 1500px;}
      div[data-testid="stMetric"] {background: #f4f7fb; border: 1px solid #dce5ee;
        border-radius: 12px; padding: 12px 14px; color: #19324d !important;}
      div[data-testid="stMetric"] * {color: #19324d !important;}
      div[data-testid="stForm"] {border: 1px solid #dce5ee; border-radius: 14px; padding: 18px;}
    </style>
    """,
    unsafe_allow_html=True,
)
st.title("ARM 305 · Edge, Fog & Cloud Task Simulator")
st.caption(
    "Set the workload and node inputs, then watch the Python simulator report every task as it is placed. "
    "All latency, capacity use and outcomes are simulated."
)

with st.form("simulation_inputs"):
    st.subheader("Workload and run settings")
    task_col, seed_col, policy_col, pacing_col = st.columns([1, 1, 1.7, 1.2])
    task_count = task_col.number_input("Number of tasks", min_value=10, max_value=200, value=20, step=1)
    seed = seed_col.number_input("Workload seed", min_value=-2_147_483_648, max_value=2_147_483_647, value=305, step=1)
    selected_mode = policy_col.selectbox("Placement policy", list(POLICY_OPTIONS))
    display_delay_ms = pacing_col.slider("Live display pace (ms/task)", min_value=0, max_value=500, value=100, step=25)
    st.caption("The display pace only makes task-by-task updates easier to follow. It does not change simulated latency.")

    st.subheader("Simulated node settings")
    default_settings = {
        "edge": {"cpu_capacity": 8, "memory_capacity_gb": 8, "base_latency_ms": 5},
        "fog": {"cpu_capacity": 16, "memory_capacity_gb": 24, "base_latency_ms": 20},
        "cloud": {"cpu_capacity": 64, "memory_capacity_gb": 64, "base_latency_ms": 50},
    }
    node_settings: dict[str, dict[str, float]] = {}
    for column, key in zip(st.columns(3), ("edge", "fog", "cloud")):
        label = NODE_LABELS[key]
        values = default_settings[key]
        with column:
            st.markdown(f"**{label} node**")
            cpu = st.number_input(f"{label} CPU capacity", min_value=1, max_value=512, value=values["cpu_capacity"], step=1, key=f"{key}_cpu")
            memory = st.number_input(f"{label} RAM capacity (GB)", min_value=1, max_value=1024, value=values["memory_capacity_gb"], step=1, key=f"{key}_ram")
            latency = st.number_input(f"{label} base latency (ms)", min_value=0, max_value=5000, value=values["base_latency_ms"], step=1, key=f"{key}_latency")
        node_settings[key] = {
            "cpu_capacity": float(cpu),
            "memory_capacity_gb": float(memory),
            "base_latency_ms": float(latency),
        }
    submitted = st.form_submit_button("Run simulation", type="primary", width="stretch")

if submitted:
    try:
        tasks = generate_seeded_tasks(int(task_count), int(seed))
        policies = POLICY_OPTIONS[selected_mode]
        configured_nodes = create_configured_nodes(node_settings)
        too_large = [
            task.task_id for task in tasks
            if not any(
                task.cpu_required <= node.cpu_capacity
                and task.memory_required_gb <= node.memory_capacity_gb
                for node in configured_nodes
            )
        ]
        if too_large:
            raise ValueError(
                f"Task {too_large[0]} is larger than every configured node. Increase at least one node's CPU and RAM capacity."
            )
    except (ValueError, TypeError) as exc:
        st.error(str(exc))
    else:
        total_steps = len(tasks) * len(policies)
        event_queue: queue.Queue[tuple[str, Any]] = queue.Queue()
        worker = threading.Thread(
            target=_run_in_background,
            args=(tasks, policies, node_settings, display_delay_ms / 1000, event_queue),
            daemon=True,
        )
        counters = {
            policy.value: {"done": 0, "placed": 0, "rejected": 0, "met": 0, "missed": 0, "latencies": []}
            for policy in policies
        }
        live_rows: list[dict[str, Any]] = []
        status = st.status("Starting simulated run…", expanded=True)
        progress = st.progress(0.0, text="Waiting for the first task result…")
        summary_slot = st.empty()
        table_slot = st.empty()
        worker.start()
        completed_runs: tuple[SimulationRun, ...] | None = None
        backend_error: str | None = None
        while worker.is_alive() or not event_queue.empty():
            try:
                event_type, payload = event_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            if event_type == "task":
                live_rows.append(task_outcome_to_row(payload))
                _update_counters(counters, payload)
                completed = len(live_rows)
                policy_name = payload.placement.policy.value
                task_id = payload.placement.task.task_id
                progress.progress(
                    completed / total_steps,
                    text=f"{policy_name} · completed {counters[policy_name]['done']} of {int(task_count)} tasks · latest: {task_id}",
                )
                _render_progress_summary(summary_slot, counters, policies, int(task_count))
                table_slot.dataframe(live_rows, hide_index=True, width="stretch")
            elif event_type == "complete":
                completed_runs = payload
            elif event_type == "error":
                backend_error = payload
        if backend_error:
            status.update(label="Simulation stopped", state="error", expanded=True)
            st.error(backend_error)
        elif completed_runs is not None:
            progress.progress(1.0, text="All task decisions are ready.")
            status.update(label="Simulation complete", state="complete", expanded=False)
            try:
                output_paths = _save_run_files(completed_runs, int(seed))
            except Exception as exc:
                output_paths = None
                st.warning(f"The simulation completed, but result files could not be saved: {exc}")
            st.session_state["latest_runs"] = completed_runs
            st.session_state["latest_seed"] = int(seed)
            st.session_state["latest_task_count"] = int(task_count)
            st.session_state["latest_outputs"] = output_paths
            st.session_state["latest_settings"] = node_settings

if "latest_runs" in st.session_state:
    st.divider()
    _render_completed_results(
        st.session_state["latest_runs"],
        st.session_state["latest_seed"],
        st.session_state["latest_task_count"],
        st.session_state.get("latest_outputs"),
    )

with st.expander("How to read these results", expanded=False):
    st.markdown(
        "- **Placed** means a node had enough remaining CPU and RAM. **Rejected** means no node could fit the task.\n"
        "- **QoS miss** means the placed task's simulated latency exceeded the target for its sensitivity. Rejected tasks have no QoS result.\n"
        "- **Tenant ID** is shown for each generated sample task. The simulator's protected-record check still limits tenant lookups to the owner.\n"
        "- **Mean latency** and node utilization are model outputs, not measurements from real hardware or a network."
    )
