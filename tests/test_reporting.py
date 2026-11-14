import csv
import json
from pathlib import Path
import tempfile
import unittest

from cdefsim import generate_seeded_tasks, run_policy_comparison
from cdefsim.reporting import (
    create_results_chart,
    format_console_report,
    write_summary_json,
    write_task_results_csv,
)


class SeededWorkloadTests(unittest.TestCase):
    def test_seeded_workload_is_repeatable_and_has_at_least_ten_tasks(self):
        first = generate_seeded_tasks(count=20, seed=305)
        second = generate_seeded_tasks(count=20, seed=305)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 20)
        self.assertEqual(len({task.latency_sensitivity for task in first}), 3)
        with self.assertRaises(ValueError):
            generate_seeded_tasks(count=9, seed=305)


class ResultsOutputTests(unittest.TestCase):
    def setUp(self):
        self.tasks = generate_seeded_tasks()
        self.runs = run_policy_comparison(self.tasks)

    def test_metrics_separate_placement_and_qos_outcomes(self):
        for run in self.runs:
            summary = run.summary
            self.assertEqual(summary.total_tasks, len(self.tasks))
            self.assertEqual(summary.placed_count + summary.rejected_count, len(self.tasks))
            self.assertEqual(summary.qos_met_count + summary.qos_missed_count, summary.placed_count)
            self.assertGreater(summary.rejected_count, 0)
            self.assertEqual(sum(summary.placements_by_node.values()), summary.placed_count)

    def test_csv_json_and_chart_are_written_and_readable(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as temporary_directory:
            output = Path(temporary_directory)
            csv_path = write_task_results_csv(self.runs, output / "tasks.csv")
            json_path = write_summary_json(self.runs, output / "summary.json", seed=305)
            chart_path = create_results_chart(self.runs, output / "chart.png")

            with csv_path.open(newline="", encoding="utf-8") as stream:
                rows = list(csv.DictReader(stream))
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(len(rows), len(self.tasks) * len(self.runs))
            self.assertIn("simulated", payload["simulation_label"].lower())
            self.assertEqual(payload["random_seed"], 305)
            self.assertEqual(payload["task_count"], len(self.tasks))
            self.assertEqual(len(payload["runs"]), 2)
            self.assertTrue(chart_path.is_file())
            self.assertGreater(chart_path.stat().st_size, 1000)

    def test_console_report_shows_task_decisions_utilization_and_totals(self):
        report = format_console_report(self.runs, seed=305)
        self.assertIn("Total=20", report)
        self.assertIn("Placement successes=", report)
        self.assertIn("Rejected=", report)
        self.assertIn("Sim latency ms", report)
        self.assertIn("Final resource utilization", report)
        self.assertIn("QoS", report)


if __name__ == "__main__":
    unittest.main()
