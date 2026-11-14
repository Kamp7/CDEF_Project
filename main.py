"""Run the seeded CDEF placement comparison and save its evidence."""

from __future__ import annotations

import argparse
from pathlib import Path

from cdefsim.engine import run_policy_comparison
from cdefsim.reporting import (
    create_results_chart,
    format_console_report,
    write_summary_json,
    write_task_results_csv,
)
from cdefsim.workloads import DEFAULT_RANDOM_SEED, DEFAULT_TASK_COUNT, generate_seeded_tasks


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run both simulated placement policies on the same fixed-seed workload."
    )
    parser.add_argument("--tasks", type=int, default=DEFAULT_TASK_COUNT, help="number of tasks (minimum 10)")
    parser.add_argument("--seed", type=int, default=DEFAULT_RANDOM_SEED, help="repeatable workload seed")
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path("results"),
        help="directory for CSV, JSON, and PNG outputs",
    )
    args = parser.parse_args()

    try:
        tasks = generate_seeded_tasks(args.tasks, args.seed)
    except ValueError as exc:
        parser.error(str(exc))
    runs = run_policy_comparison(tasks)

    print(format_console_report(runs, args.seed))
    args.results_dir.mkdir(parents=True, exist_ok=True)
    csv_path = write_task_results_csv(runs, args.results_dir / "task_results.csv")
    json_path = write_summary_json(runs, args.results_dir / "run_summary.json", seed=args.seed)
    chart_path = create_results_chart(runs, args.results_dir / "placement_utilization_qos.png")
    print("\nSaved simulated evidence:")
    print(f"  Per-task CSV: {csv_path.resolve()}")
    print(f"  Summary JSON: {json_path.resolve()}")
    print(f"  Chart PNG:    {chart_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
