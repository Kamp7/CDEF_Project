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
python main.py
```

The default run generates 20 tasks using seed `305`, then compares both
placement policies on that same workload. Repeat it with the same seed to get
the same task inputs and decisions:

```powershell
python main.py --tasks 20 --seed 305
```

The task count must be at least 10. A different seed or count can be selected;
the selected values are printed and the seed is included in the run output.

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

Rebuild the report and architecture SVG after regenerating the experiments with:

```powershell
python scripts/build_report.py
```

The report builder uses the saved CSV/JSON results in `results/experiments/` and
the existing simulated-results chart. The PowerPoint is included as a submission
artifact; running the simulator itself needs only Python and the packages in
`requirements.txt`.
