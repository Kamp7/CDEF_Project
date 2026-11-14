import unittest
from dataclasses import FrozenInstanceError

from cdefsim import (
    AccessDenied,
    LatencySensitivity,
    Node,
    NodeType,
    PlacementPolicy,
    PlacementStatus,
    Task,
    TenantTaskStore,
    VMManager,
    VMStatus,
    create_default_nodes,
    place_task,
)


def make_task(task_id="task-1", tenant_id="tenant-a", cpu=1, memory=1, sensitivity="medium"):
    return Task(task_id, tenant_id, cpu, memory, sensitivity)


class NodeAndTaskTests(unittest.TestCase):
    def test_default_nodes_include_each_compute_tier(self):
        nodes = create_default_nodes()
        self.assertEqual(
            {node.node_type for node in nodes},
            {NodeType.EDGE, NodeType.FOG, NodeType.CLOUD},
        )
        self.assertTrue(all(node.cpu_capacity > 0 and node.memory_capacity_gb > 0 for node in nodes))

    def test_node_requires_both_cpu_and_memory_to_fit(self):
        node = Node("edge-a", "Edge", cpu_capacity=8, memory_capacity_gb=8, base_latency_ms=5)
        node.reserve(7, 2)
        self.assertFalse(node.can_fit(2, 1))
        self.assertFalse(node.can_fit(1, 7))
        self.assertTrue(node.can_fit(1, 6))

    def test_task_validates_resources_and_latency_sensitivity(self):
        with self.assertRaises(ValueError):
            make_task(cpu=0)
        with self.assertRaises(ValueError):
            make_task(memory=-1)
        with self.assertRaises(ValueError):
            make_task(sensitivity="urgent")
        self.assertIs(make_task(sensitivity="high").latency_sensitivity, LatencySensitivity.HIGH)


class PlacementTests(unittest.TestCase):
    def setUp(self):
        # Edge has a lower projected latency but higher projected utilization.
        self.edge = Node("edge-a", "Edge", cpu_capacity=10, memory_capacity_gb=10, base_latency_ms=5)
        self.fog = Node("fog-a", "Fog", cpu_capacity=100, memory_capacity_gb=100, base_latency_ms=20)
        self.edge.reserve(5, 5)
        self.nodes = [self.edge, self.fog]
        self.task = make_task(cpu=2, memory=2)

    def test_lowest_latency_first_uses_projected_latency(self):
        result = place_task(self.task, self.nodes, PlacementPolicy.LOWEST_LATENCY_FIRST)
        self.assertEqual(result.node_id, "edge-a")
        self.assertAlmostEqual(result.simulated_latency_ms, 19.0)
        self.assertIs(result.status, PlacementStatus.PLACED)

    def test_capacity_aware_minimizes_projected_utilization(self):
        result = place_task(self.task, self.nodes, PlacementPolicy.CAPACITY_AWARE)
        self.assertEqual(result.node_id, "fog-a")
        self.assertAlmostEqual(result.projected_cpu_utilization, 0.02)

    def test_ties_are_independent_of_node_input_order(self):
        workload = make_task(cpu=1, memory=1)
        for policy in PlacementPolicy:
            forward = [Node("z-node", "Edge", 10, 10, 10), Node("a-node", "Fog", 10, 10, 10)]
            reverse = [Node("a-node", "Fog", 10, 10, 10), Node("z-node", "Edge", 10, 10, 10)]
            result_forward = place_task(workload, forward, policy)
            result_reverse = place_task(workload, reverse, policy)
            self.assertEqual(result_forward.node_id, "a-node")
            self.assertEqual(result_reverse.node_id, "a-node")

    def test_placement_falls_back_to_an_eligible_node(self):
        edge = Node("edge-1", "Edge", 2, 1, 5)
        fog = Node("fog-1", "Fog", 4, 4, 20)
        result = place_task(make_task(cpu=2, memory=2), [edge, fog], "lowest-latency-first")
        self.assertEqual(result.node_id, "fog-1")
        self.assertEqual(edge.reserved_cpu, 0)

    def test_overload_is_rejected_without_changing_resources(self):
        nodes = [Node("edge-1", "Edge", 2, 2, 5), Node("fog-1", "Fog", 2, 2, 20)]
        first = place_task(make_task("first", cpu=2, memory=2), nodes, "capacity-aware")
        second = place_task(make_task("second", cpu=2, memory=2), nodes, "capacity-aware")
        third = place_task(make_task("third", cpu=2, memory=2), nodes, "capacity-aware")
        self.assertIs(first.status, PlacementStatus.PLACED)
        self.assertIs(second.status, PlacementStatus.PLACED)
        self.assertIs(third.status, PlacementStatus.REJECTED)
        self.assertIsNone(third.node_id)
        self.assertIsNone(third.simulated_latency_ms)
        self.assertTrue(all(node.reserved_cpu == 2 and node.reserved_memory_gb == 2 for node in nodes))

    def test_task_larger_than_all_node_capacities_is_invalid(self):
        with self.assertRaises(ValueError):
            place_task(make_task(cpu=101, memory=2), self.nodes, "capacity-aware")


class VMManagerTests(unittest.TestCase):
    def test_create_and_stop_reserve_then_release_node_resources(self):
        node = Node("fog-1", "Fog", 8, 12, 20)
        manager = VMManager([node])
        vm = manager.create("vm-1", "fog-1", allocated_cpu=3, allocated_memory_gb=5)
        self.assertIs(vm.status, VMStatus.RUNNING)
        self.assertEqual((vm.vm_id, vm.host_node_id), ("vm-1", "fog-1"))
        self.assertEqual((node.reserved_cpu, node.reserved_memory_gb), (3, 5))
        with self.assertRaises(FrozenInstanceError):
            vm.status = VMStatus.STOPPED

        stopped = manager.stop("vm-1")
        self.assertIs(stopped.status, VMStatus.STOPPED)
        self.assertEqual((node.reserved_cpu, node.reserved_memory_gb), (0, 0))
        manager.stop("vm-1")  # Stopping twice must not release resources twice.
        self.assertEqual((node.reserved_cpu, node.reserved_memory_gb), (0, 0))

    def test_rejects_duplicate_ids_unknown_hosts_and_non_fitting_allocations(self):
        node = Node("fog-1", "Fog", 8, 12, 20)
        manager = VMManager([node])
        manager.create("vm-1", "fog-1", 2, 2)
        with self.assertRaises(ValueError):
            manager.create("vm-1", "fog-1", 1, 1)
        with self.assertRaises(ValueError):
            manager.create("vm-2", "missing", 1, 1)
        with self.assertRaises(ValueError):
            manager.create("vm-3", "fog-1", 7, 2)
        self.assertEqual((node.reserved_cpu, node.reserved_memory_gb), (2, 2))

    def test_rejects_invalid_allocations_and_unknown_vm_stop(self):
        node = Node("fog-1", "Fog", 8, 12, 20)
        manager = VMManager([node])
        with self.assertRaises(ValueError):
            manager.create("vm-1", "fog-1", 0, 1)
        with self.assertRaises(ValueError):
            manager.create("", "fog-1", 1, 1)
        with self.assertRaises(ValueError):
            manager.stop("missing")
        self.assertEqual((node.reserved_cpu, node.reserved_memory_gb), (0, 0))


class TenantIsolationTests(unittest.TestCase):
    def test_tenant_can_read_own_record_but_not_another_tenants(self):
        nodes = create_default_nodes()
        own = place_task(make_task("secret-task", "tenant-a"), nodes, "lowest-latency-first")
        other = place_task(make_task("other-task", "tenant-b"), nodes, "lowest-latency-first")
        store = TenantTaskStore()
        store.record(own)
        store.record(other)

        self.assertIs(store.get("tenant-a", "secret-task"), own)
        self.assertEqual([r.task.task_id for r in store.list_for("tenant-b")], ["other-task"])
        with self.assertRaises(AccessDenied) as denied:
            store.get("tenant-b", "secret-task")
        self.assertNotIn("secret-task", str(denied.exception))
        self.assertNotIn("tenant-a", str(denied.exception))
        self.assertEqual(store.list_for("unknown-tenant"), ())

    def test_missing_and_unauthorized_records_have_same_denial(self):
        store = TenantTaskStore()
        with self.assertRaises(AccessDenied) as missing:
            store.get("tenant-b", "missing-task")

        store.record(place_task(make_task("secret-task", "tenant-a"), create_default_nodes(), "capacity-aware"))
        with self.assertRaises(AccessDenied) as unauthorized:
            store.get("tenant-b", "secret-task")
        self.assertEqual(str(missing.exception), str(unauthorized.exception))

    def test_store_rejects_duplicate_task_ids(self):
        store = TenantTaskStore()
        store.record(place_task(make_task("same-id", "tenant-a"), create_default_nodes(), "capacity-aware"))
        with self.assertRaises(ValueError):
            store.record(place_task(make_task("same-id", "tenant-b"), create_default_nodes(), "capacity-aware"))


if __name__ == "__main__":
    unittest.main()
