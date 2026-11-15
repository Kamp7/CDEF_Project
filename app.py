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
NODE_META = {
    "edge": ("EDGE", "Lowest configured delay", "node-edge"),
    "fog": ("FOG", "Balanced intermediate tier", "node-fog"),
    "cloud": ("CLOUD", "Largest resource pool", "node-cloud"),
}


def _policy_title(policy: PlacementPolicy | str) -> str:
    value = policy.value if isinstance(policy, PlacementPolicy) else str(policy)
    return value.replace("-", " ").title()


def _metric_card(label: str, value: str | int, tone: str = "neutral") -> None:
    st.markdown(
        f"""
        <div class="metric-card metric-{tone}">
          <div class="metric-label">{label}</div>
          <div class="metric-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _metric_row(cards: list[tuple[str, str | int, str]]) -> None:
    columns = st.columns(len(cards))
    for column, (label, value, tone) in zip(columns, cards):
        with column:
            _metric_card(label, value, tone)


def _section_header(kicker: str, title: str, description: str) -> None:
    st.markdown(
        f"""
        <div class="section-heading">
          <span>{kicker}</span>
          <h2>{title}</h2>
          <p>{description}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


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
                mean_latency = (
                    sum(values["latencies"]) / len(values["latencies"])
                    if values["latencies"] else None
                )
                with st.container(border=True):
                    st.markdown(
                        f'<div class="policy-title"><span class="live-dot"></span>{_policy_title(policy)}</div>',
                        unsafe_allow_html=True,
                    )
                    _metric_row([
                        ("Processed", f"{values['done']} / {task_count}", "info"),
                        ("Placed", values["placed"], "success"),
                        ("Rejected", values["rejected"], "danger"),
                    ])
                    _metric_row([
                        ("QoS met", values["met"], "success"),
                        ("QoS missed", values["missed"], "warning"),
                        ("Mean latency", f"{mean_latency:.2f} ms" if mean_latency is not None else "—", "neutral"),
                    ])


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
    _section_header(
        "RESULTS",
        "Simulation summary",
        f"Seed {seed} · {task_count} generated tasks · all latency and resource values are simulated.",
    )
    for run in runs:
        summary = run.summary
        with st.container(border=True):
            st.markdown(
                f'<div class="policy-title"><span class="policy-icon">◆</span>{_policy_title(run.policy)}</div>',
                unsafe_allow_html=True,
            )
            _metric_row([
                ("Total tasks", summary.total_tasks, "info"),
                ("Placed", summary.placed_count, "success"),
                ("Rejected", summary.rejected_count, "danger"),
                ("QoS met", summary.qos_met_count, "success"),
                ("QoS missed", summary.qos_missed_count, "warning"),
                (
                    "Mean latency",
                    f"{summary.mean_simulated_latency_ms:.2f} ms"
                    if summary.mean_simulated_latency_ms is not None else "—",
                    "neutral",
                ),
            ])
            placement_text = " · ".join(
                f"{node_id}: {count}" for node_id, count in summary.placements_by_node.items()
            )
            st.markdown(
                f'<div class="summary-note"><strong>Placement by node</strong> · {placement_text} '
                '<span>QoS is evaluated only for placed tasks.</span></div>',
                unsafe_allow_html=True,
            )

    all_rows = [
        task_outcome_to_row(outcome)
        for run in runs
        for outcome in run.task_outcomes
    ]
    utilization_rows = []
    for run in runs:
        for node in run.node_usage:
            utilization_rows.append({
                "Policy": run.policy.value,
                "Node": node.node_id,
                "Tier": node.node_type,
                "CPU used / capacity": f"{node.cpu_used:g} / {node.cpu_capacity:g}",
                "CPU utilization (%)": node.cpu_utilization_percent,
                "RAM used / capacity (GB)": f"{node.memory_used_gb:g} / {node.memory_capacity_gb:g}",
                "RAM utilization (%)": node.memory_utilization_percent,
                "Base latency": f"{node.base_latency_ms:g} ms",
            })

    task_tab, utilization_tab, evidence_tab = st.tabs(
        ["Task explorer", "Node utilization", "Evidence & chart"]
    )
    with task_tab:
        st.markdown("#### Filter and inspect every task")
        st.caption("Use the filters to isolate a tenant, policy, placement outcome, or QoS result.")
        policy_options = sorted({row["Policy"] for row in all_rows})
        tenant_options = sorted({row["Tenant ID"] for row in all_rows})
        filter_key = f"{seed}_{task_count}_{'_'.join(policy_options)}"
        filter_columns = st.columns(4)
        selected_policies = filter_columns[0].multiselect(
            "Policy", policy_options, default=policy_options, key=f"policy_{filter_key}"
        )
        selected_tenants = filter_columns[1].multiselect(
            "Tenant", tenant_options, default=tenant_options, key=f"tenant_{filter_key}"
        )
        selected_placements = filter_columns[2].multiselect(
            "Placement", ["Placed", "Rejected"], default=["Placed", "Rejected"], key=f"placement_{filter_key}"
        )
        selected_qos = filter_columns[3].multiselect(
            "QoS", ["Met", "Miss", "Not evaluated"], default=["Met", "Miss", "Not evaluated"], key=f"qos_{filter_key}"
        )
        filtered_rows = [
            row for row in all_rows
            if row["Policy"] in selected_policies
            and row["Tenant ID"] in selected_tenants
            and row["Placement"] in selected_placements
            and row["QoS"] in selected_qos
        ]
        st.caption(f"Showing {len(filtered_rows)} of {len(all_rows)} task records")
        if filtered_rows:
            st.dataframe(filtered_rows, hide_index=True, width="stretch", height=500)
        else:
            st.info("No task records match the selected filters.")

    with utilization_tab:
        st.markdown("#### Final node resource use")
        st.caption("The bars show final utilization; it is also peak utilization in this reservation model.")
        st.dataframe(
            utilization_rows,
            hide_index=True,
            width="stretch",
            column_config={
                "CPU utilization (%)": st.column_config.ProgressColumn(
                    "CPU utilization", min_value=0, max_value=100, format="%.1f%%"
                ),
                "RAM utilization (%)": st.column_config.ProgressColumn(
                    "RAM utilization", min_value=0, max_value=100, format="%.1f%%"
                ),
            },
        )

    with evidence_tab:
        if output_paths:
            evidence_left, evidence_right = st.columns([1.7, 1])
            with evidence_left:
                st.image(
                    str(output_paths["chart"]),
                    caption="Simulated placement, utilization and QoS",
                    width="stretch",
                )
            with evidence_right:
                st.markdown("#### Export this run")
                st.caption(f"Saved under `{output_paths['csv'].parent.relative_to(PROJECT_ROOT)}`")
                st.download_button(
                    "Download task CSV",
                    data=output_paths["csv"].read_bytes(),
                    file_name=f"task_results_seed_{seed}_{task_count}.csv",
                    mime="text/csv",
                    width="stretch",
                )
                st.download_button(
                    "Download summary JSON",
                    data=output_paths["json"].read_bytes(),
                    file_name=f"run_summary_seed_{seed}_{task_count}.json",
                    mime="application/json",
                    width="stretch",
                )
                st.download_button(
                    "Download chart PNG",
                    data=output_paths["chart"].read_bytes(),
                    file_name=f"placement_utilization_qos_seed_{seed}_{task_count}.png",
                    mime="image/png",
                    width="stretch",
                )
                st.info("These files are generated from this exact simulator run.")
        else:
            st.info("The run completed, but no evidence files are available for download.")


st.set_page_config(page_title="ARM 305 Task Placement Simulator", page_icon="☁️", layout="wide")
st.markdown(
    """
    <style>
      :root {
        --navy: #17324d;
        --ink: #263b4f;
        --muted: #66798b;
        --teal: #138a86;
        --blue: #3976a8;
        --green: #27845f;
        --amber: #b87512;
        --red: #c84e55;
        --border: #d9e3eb;
        --surface: #ffffff;
        --soft: #f4f7fa;
      }
      .stApp {background: linear-gradient(180deg, #f6f9fb 0, #ffffff 360px); color: var(--ink);}
      .block-container {padding-top: 1.25rem; padding-bottom: 3rem; max-width: 1440px;}
      .hero {
        display: grid; grid-template-columns: 1.45fr 0.75fr; gap: 32px; align-items: center;
        background: linear-gradient(125deg, #17324d 0%, #214a64 58%, #147f7d 100%);
        border-radius: 24px; padding: 34px 40px; margin-bottom: 24px;
        box-shadow: 0 18px 45px rgba(23, 50, 77, .16); color: white;
      }
      .hero-kicker {font-size: 12px; font-weight: 800; letter-spacing: .16em; color: #89e0d9;}
      .hero h1 {font-size: 38px; line-height: 1.12; margin: 10px 0 12px; color: white; letter-spacing: -.025em;}
      .hero p {margin: 0; color: #dce9f2; font-size: 16px; line-height: 1.55; max-width: 760px;}
      .hero-stats {display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px;}
      .hero-stat {background: rgba(255,255,255,.1); border: 1px solid rgba(255,255,255,.18); border-radius: 14px; padding: 16px 12px; text-align: center;}
      .hero-stat strong {display: block; color: white; font-size: 24px; line-height: 1; margin-bottom: 7px;}
      .hero-stat span {color: #dce9f2; font-size: 11px; line-height: 1.25;}
      .section-heading {margin: 28px 0 14px;}
      .section-heading span {font-size: 11px; font-weight: 800; letter-spacing: .14em; color: var(--teal);}
      .section-heading h2 {font-size: 28px; line-height: 1.2; color: var(--navy); margin: 5px 0; letter-spacing: -.02em;}
      .section-heading p {font-size: 14px; color: var(--muted); margin: 0;}
      div[data-testid="stForm"] {background: rgba(255,255,255,.96); border: 1px solid var(--border); border-radius: 20px; padding: 24px; box-shadow: 0 10px 30px rgba(23,50,77,.07);}
      div[data-testid="stVerticalBlockBorderWrapper"] {border-color: var(--border) !important; border-radius: 16px !important; background: var(--surface);}
      .node-heading {display:flex; align-items:center; justify-content:space-between; gap:12px; margin-bottom:4px;}
      .node-heading strong {color: var(--navy); font-size: 17px;}
      .node-chip {font-size:10px; font-weight:800; letter-spacing:.1em; padding:5px 8px; border-radius:999px;}
      .node-edge {background:#e5f2fb; color:#286a9c;}
      .node-fog {background:#e6f5f1; color:#187d69;}
      .node-cloud {background:#fff1d9; color:#9b6410;}
      .node-description {color:var(--muted); font-size:12px; margin-bottom:14px;}
      .policy-title {display:flex; align-items:center; gap:9px; color:var(--navy); font-size:18px; font-weight:800; margin:2px 0 12px;}
      .policy-icon {color:var(--teal); font-size:13px;}
      .live-dot {width:9px; height:9px; border-radius:50%; background:#2ca977; box-shadow:0 0 0 5px rgba(44,169,119,.12);}
      .metric-card {min-height:82px; border-radius:14px; padding:13px 14px; border:1px solid var(--border); background:var(--soft); overflow:hidden;}
      .metric-label {font-size:11px; font-weight:700; color:var(--muted); white-space:nowrap; overflow:hidden; text-overflow:ellipsis;}
      .metric-value {font-size:clamp(18px, 1.7vw, 24px); font-weight:800; line-height:1.2; color:var(--navy); margin-top:7px; white-space:nowrap;}
      .metric-success {background:#eef8f3; border-color:#cbe9da;}
      .metric-success .metric-value {color:var(--green);}
      .metric-danger {background:#fff2f2; border-color:#f1d1d4;}
      .metric-danger .metric-value {color:var(--red);}
      .metric-warning {background:#fff8e9; border-color:#f1dfb9;}
      .metric-warning .metric-value {color:var(--amber);}
      .metric-info {background:#eef5fb; border-color:#d4e4f1;}
      .metric-info .metric-value {color:var(--blue);}
      .summary-note {background:#f6f9fb; border-radius:10px; padding:10px 12px; margin-top:5px; color:var(--muted); font-size:12px;}
      .summary-note strong {color:var(--navy);}
      .summary-note span {float:right;}
      div[data-testid="stTabs"] [data-baseweb="tab-list"] {gap:8px; border-bottom:1px solid var(--border);}
      div[data-testid="stTabs"] button[role="tab"] {border-radius:10px 10px 0 0; padding:10px 18px; color:var(--muted); font-weight:700;}
      div[data-testid="stTabs"] button[aria-selected="true"] {color:var(--teal); background:#edf7f6;}
      div[data-testid="stDataFrame"] {border:1px solid var(--border); border-radius:14px; overflow:hidden;}
      div[data-testid="stDownloadButton"] button, div[data-testid="stFormSubmitButton"] button {min-height:46px; border-radius:11px; font-weight:800;}
      div[data-testid="stFormSubmitButton"] button {background:linear-gradient(90deg,#137f7c,#159b91); border:0; box-shadow:0 7px 18px rgba(19,138,134,.22);}
      div[data-baseweb="input"] > div, div[data-baseweb="select"] > div {border-radius:10px;}
      @media (max-width: 900px) {
        .hero {grid-template-columns:1fr; padding:28px 24px;}
        .hero h1 {font-size:31px;}
        .summary-note span {float:none; display:block; margin-top:5px;}
        .metric-value {font-size:20px;}
      }
    </style>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    """
    <section class="hero">
      <div>
        <div class="hero-kicker">ARM 305 · MINI PROJECT</div>
        <h1>Edge, Fog & Cloud Task Lab</h1>
        <p>Configure a repeatable workload, compare placement policies, and watch every task move through the simulated infrastructure in real time.</p>
      </div>
      <div class="hero-stats">
        <div class="hero-stat"><strong>3</strong><span>compute tiers</span></div>
        <div class="hero-stat"><strong>2</strong><span>placement policies</span></div>
        <div class="hero-stat"><strong>LIVE</strong><span>task decisions</span></div>
      </div>
    </section>
    """,
    unsafe_allow_html=True,
)

_section_header(
    "CONFIGURE",
    "Build your simulation run",
    "Choose the workload, policy, playback pace, and resource profile for each simulated tier.",
)

with st.form("simulation_inputs"):
    st.markdown("### Workload")
    task_col, seed_col, policy_col, pacing_col = st.columns([1, 1, 1.7, 1.2])
    task_count = task_col.number_input("Number of tasks", min_value=10, max_value=200, value=20, step=1)
    seed = seed_col.number_input("Workload seed", min_value=-2_147_483_648, max_value=2_147_483_647, value=305, step=1)
    selected_mode = policy_col.selectbox("Placement policy", list(POLICY_OPTIONS))
    display_delay_ms = pacing_col.slider("Live display pace (ms/task)", min_value=0, max_value=500, value=100, step=25)
    st.caption("Display pace controls only the animation speed. It never changes the simulated latency result.")

    st.markdown("### Compute tiers")
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
            with st.container(border=True):
                chip, description, css_class = NODE_META[key]
                st.markdown(
                    f'<div class="node-heading"><strong>{label} node</strong><span class="node-chip {css_class}">{chip}</span></div>'
                    f'<div class="node-description">{description}</div>',
                    unsafe_allow_html=True,
                )
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
        _section_header(
            "LIVE RUN",
            "Processing task decisions",
            "The backend publishes each placement and QoS decision as soon as it completes.",
        )
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
                table_slot.dataframe(live_rows, hide_index=True, width="stretch", height=430)
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
