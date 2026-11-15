# ARM 305 CDEF Simulator

A locally runnable Python simulator for assigning computing tasks to simulated
Edge, Fog, and Cloud nodes. It uses in-memory VM records and tenant-scoped task
records; it does not connect to cloud services or create real VMs.

## Setup and run

Python 3.10 or newer is recommended.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Open `http://127.0.0.1:8501` in your browser. The project Streamlit
settings bind the app to `127.0.0.1`, so it is available only from this
computer.

The page accepts the task count, seed, placement policy, Edge/Fog/Cloud CPU and
RAM capacities, and configured base latencies. After **Run simulation**, it
streams each task's tenant ID, selected node, placement status, simulated
latency, and QoS result to the table as the backend processes the workload.
The live display pace is only for readability; it does not affect simulated
latency. Completed UI runs are saved in a new folder under `results/ui_runs/`
with a task CSV, summary JSON, and chart. The existing `python main.py` CLI
continues to work.

The UI defaults to 20 tasks and seed `305`. Select either policy or compare both
on that same generated workload. For an optional command-line run, repeat the
same count and seed to get the same task inputs and decisions:

```powershell
python main.py --tasks 20 --seed 305
```

Both interfaces require at least 10 tasks. In command-line mode, a different
seed or count can be selected; those values are printed and the seed is
included in the saved run output.

## Policies and simulated assumptions

- **Lowest-latency-first** chooses the eligible node with the lowest projected
  latency. Ties are resolved by stable node ID.
- **Capacity-aware** chooses the eligible node with the lowest projected
  bottleneck utilization (the larger of projected CPU and RAM use); projected
  latency breaks ties, followed by stable node ID.
- Each node has CPU capacity, RAM capacity, and configured base latency. The
  default Edge/Fog/Cloud capacities are 8/8 GB, 16/24 GB, and 64/64 GB; base
  latencies are 5, 20, and 50 ms. These are configurable simulation defaults,
  not course-provided measurements.
- Projected latency is base latency plus 20 ms multiplied by projected
  bottleneck utilization. QoS target assumptions are high 25 ms, medium 60 ms,
  and low 100 ms. The task's sensitivity is reported and evaluated against its
  target; it does not change either policy's ranking.
- Accepted tasks reserve CPU and RAM until their policy run ends. Each policy
  starts with fresh nodes, making the comparison repeatable. Final utilization
  therefore equals peak utilization for these runs.
- A task is placed if at least one node has enough remaining CPU and RAM.
  Placement acceptance and QoS success are reported separately. A task with no
  eligible node is rejected; a task that is placed may still miss its QoS
  target. All values are simulated.

## Outputs

Each run prints per-task placement, simulated latency, target, QoS outcome,
resource utilization, and totals. It writes:

- `results/task_results.csv` - one row per task and policy.
- `results/run_summary.json` - totals, node utilization, and assumptions.
- `results/placement_utilization_qos.png` - labeled placement, utilization,
  and QoS chart.

## Focused checks

```powershell
python -m unittest discover -s tests -v
```

## Required experiments

Run all four repeatable experiment scenarios and write setup/expected/actual
outcomes plus supporting data to `results/experiments/`:

```powershell
python scripts/run_experiments.py
```

The evidence includes a same-seed policy comparison, an overload trace showing
Edge eligibility/fallback/rejection, a tenant-isolation denial record, and a
same-workload comparison after increasing Cloud RAM from 64 GB to 96 GB.
`results/experiments/experiment_log.md` links the CSV, JSON, and chart evidence.

## Submission materials

- [Architecture diagram source](docs/architecture.mmd) and [standalone SVG](docs/architecture.svg).
- [Verified 7-page project report](output/pdf/arm305_mini_project_report.pdf).
- [6-slide presentation](output/presentation/arm305_mini_project_slides_submission.pptx).
- [7-slide English project explainer](output/presentation/arm305_project_explainer_english_final_v3.pptx).

Rebuild the report and architecture SVG after regenerating the experiments with:

```powershell
python scripts/build_report.py
```

The report builder uses the saved CSV/JSON results in `results/experiments/` and
the existing simulated-results chart. The PowerPoint is included as a submission
artifact; running the simulator itself needs only Python and the packages in
`requirements.txt`.
