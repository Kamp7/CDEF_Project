import unittest

from cdefsim import (
    Node,
    PlacementPolicy,
    Task,
    generate_seeded_tasks,
    run_policy,
)
from cdefsim.ui_support import create_configured_nodes, task_outcome_to_row


class LiveProgressTests(unittest.TestCase):
    def test_run_policy_notifies_observer_once_per_completed_task(self):
        tasks = generate_seeded_tasks(count=10, seed=305)
        observed = []

        run = run_policy(
            tasks,
            PlacementPolicy.LOWEST_LATENCY_FIRST,
            on_task_complete=observed.append,
        )

        self.assertEqual(observed, list(run.task_outcomes))
        self.assertEqual(len(observed), len(tasks))

    def test_configured_node_settings_are_applied_to_fresh_pools(self):
        settings = {
            "edge": {"cpu_capacity": 4, "memory_capacity_gb": 6, "base_latency_ms": 3},
            "fog": {"cpu_capacity": 12, "memory_capacity_gb": 20, "base_latency_ms": 18},
            "cloud": {"cpu_capacity": 80, "memory_capacity_gb": 96, "base_latency_ms": 55},
        }

        first_pool = create_configured_nodes(settings)
        second_pool = create_configured_nodes(settings)

        self.assertEqual([node.node_id for node in first_pool], ["edge-1", "fog-1", "cloud-1"])
        self.assertEqual(first_pool[2].cpu_capacity, 80)
        self.assertEqual(first_pool[2].memory_capacity_gb, 96)
        self.assertEqual(first_pool[2].base_latency_ms, 55)
        self.assertIsNot(first_pool[0], second_pool[0])

    def test_live_row_contains_tenant_placement_latency_and_qos_miss(self):
        task = Task("task-live", "tenant-demo", 1, 1, "high")
        node = Node("cloud-1", "Cloud", 10, 10, 60)
        outcome = run_policy([task], "lowest-latency-first", nodes=[node]).task_outcomes[0]

        row = task_outcome_to_row(outcome)

        self.assertEqual(row["Tenant ID"], "tenant-demo")
        self.assertEqual(row["Node"], "cloud-1")
        self.assertEqual(row["Placement"], "Placed")
        self.assertEqual(row["QoS"], "Miss")
        self.assertTrue(row["Simulated latency"].endswith(" ms"))

    def test_live_row_marks_rejection_without_a_latency_or_qos_result(self):
        tasks = [
            Task("task-first", "tenant-a", 1, 1, "medium"),
            Task("task-next", "tenant-b", 1, 1, "medium"),
        ]
        outcome = run_policy(
            tasks,
            "lowest-latency-first",
            nodes=[Node("edge-1", "Edge", 1, 1, 5)],
        ).task_outcomes[1]

        row = task_outcome_to_row(outcome)

        self.assertEqual(row["Tenant ID"], "tenant-b")
        self.assertEqual(row["Node"], "—")
        self.assertEqual(row["Placement"], "Rejected")
        self.assertEqual(row["Simulated latency"], "—")
        self.assertEqual(row["QoS"], "Not evaluated")


if __name__ == "__main__":
    unittest.main()
