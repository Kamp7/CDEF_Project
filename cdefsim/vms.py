"""In-memory VM records that reserve and release simulated node resources."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import replace

from .models import Node, VM, VMStatus


class VMManager:
    def __init__(self, nodes: Iterable[Node]) -> None:
        node_list = list(nodes)
        if any(not isinstance(node, Node) for node in node_list):
            raise TypeError("nodes must contain Node instances.")
        self._nodes = {node.node_id: node for node in node_list}
        if len(self._nodes) != len(node_list):
            raise ValueError("Node IDs must be unique.")
        self._vms: dict[str, VM] = {}

    @property
    def vms(self) -> tuple[VM, ...]:
        return tuple(self._vms.values())

    def create(
        self,
        vm_id: str,
        host_node_id: str,
        allocated_cpu: float,
        allocated_memory_gb: float,
    ) -> VM:
        if vm_id in self._vms:
            raise ValueError("A VM with this ID already exists.")
        if host_node_id not in self._nodes:
            raise ValueError("Unknown VM host node.")
        # Validate the complete record before reserving resources, so invalid
        # IDs cannot leave CPU/RAM reserved without a corresponding VM.
        vm = VM(
            vm_id=vm_id,
            host_node_id=host_node_id,
            allocated_cpu=allocated_cpu,
            allocated_memory_gb=allocated_memory_gb,
        )
        host = self._nodes[host_node_id]
        # Node.reserve validates positive allocations and available CPU/RAM.
        host.reserve(allocated_cpu, allocated_memory_gb)
        self._vms[vm_id] = vm
        return vm

    def stop(self, vm_id: str) -> VM:
        vm = self._vms.get(vm_id)
        if vm is None:
            raise ValueError("Unknown VM ID.")
        if vm.status is VMStatus.RUNNING:
            host = self._nodes[vm.host_node_id]
            host.release(vm.allocated_cpu, vm.allocated_memory_gb)
            vm = replace(vm, status=VMStatus.STOPPED)
            self._vms[vm_id] = vm
        return vm
