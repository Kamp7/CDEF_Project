"""Small in-memory models for the CDEF simulator."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math


_EPSILON = 1e-9


def _require_name(value: str, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string.")


def _require_positive(value: float, label: str) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value <= 0
    ):
        raise ValueError(f"{label} must be a positive finite number.")


def _require_nonnegative(value: float, label: str) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0
    ):
        raise ValueError(f"{label} must be a non-negative finite number.")


class NodeType(str, Enum):
    EDGE = "Edge"
    FOG = "Fog"
    CLOUD = "Cloud"


class LatencySensitivity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class PlacementPolicy(str, Enum):
    LOWEST_LATENCY_FIRST = "lowest-latency-first"
    CAPACITY_AWARE = "capacity-aware"


class PlacementStatus(str, Enum):
    PLACED = "placed"
    REJECTED = "rejected"


class VMStatus(str, Enum):
    RUNNING = "running"
    STOPPED = "stopped"


@dataclass
class Node:
    """A simulated compute node with shared CPU and memory reservations."""

    node_id: str
    node_type: NodeType | str
    cpu_capacity: float
    memory_capacity_gb: float
    base_latency_ms: float
    reserved_cpu: float = 0.0
    reserved_memory_gb: float = 0.0

    def __post_init__(self) -> None:
        _require_name(self.node_id, "node_id")
        try:
            self.node_type = NodeType(self.node_type)
        except ValueError as exc:
            raise ValueError("node_type must be Edge, Fog, or Cloud.") from exc
        _require_positive(self.cpu_capacity, "cpu_capacity")
        _require_positive(self.memory_capacity_gb, "memory_capacity_gb")
        _require_nonnegative(self.base_latency_ms, "base_latency_ms")
        _require_nonnegative(self.reserved_cpu, "reserved_cpu")
        _require_nonnegative(self.reserved_memory_gb, "reserved_memory_gb")
        if self.reserved_cpu > self.cpu_capacity + _EPSILON:
            raise ValueError("reserved_cpu cannot exceed cpu_capacity.")
        if self.reserved_memory_gb > self.memory_capacity_gb + _EPSILON:
            raise ValueError("reserved_memory_gb cannot exceed memory_capacity_gb.")

    @property
    def remaining_cpu(self) -> float:
        return max(0.0, self.cpu_capacity - self.reserved_cpu)

    @property
    def remaining_memory_gb(self) -> float:
        return max(0.0, self.memory_capacity_gb - self.reserved_memory_gb)

    @property
    def cpu_utilization(self) -> float:
        return self.reserved_cpu / self.cpu_capacity

    @property
    def memory_utilization(self) -> float:
        return self.reserved_memory_gb / self.memory_capacity_gb

    @property
    def projected_resource_utilization(self) -> float:
        """Return the larger of current CPU and memory utilization ratios."""
        return max(self.cpu_utilization, self.memory_utilization)

    def can_fit(self, cpu: float, memory_gb: float) -> bool:
        _require_positive(cpu, "cpu requirement")
        _require_positive(memory_gb, "memory requirement")
        return (
            cpu <= self.remaining_cpu + _EPSILON
            and memory_gb <= self.remaining_memory_gb + _EPSILON
        )

    def projected_utilizations(self, cpu: float, memory_gb: float) -> tuple[float, float]:
        """Return CPU and memory utilization after a proposed reservation."""
        if not self.can_fit(cpu, memory_gb):
            raise ValueError("The proposed reservation does not fit on this node.")
        return (
            (self.reserved_cpu + cpu) / self.cpu_capacity,
            (self.reserved_memory_gb + memory_gb) / self.memory_capacity_gb,
        )

    def reserve(self, cpu: float, memory_gb: float) -> None:
        if not self.can_fit(cpu, memory_gb):
            raise ValueError("The requested CPU and memory do not fit on this node.")
        self.reserved_cpu += cpu
        self.reserved_memory_gb += memory_gb

    def release(self, cpu: float, memory_gb: float) -> None:
        _require_positive(cpu, "CPU release")
        _require_positive(memory_gb, "memory release")
        if cpu > self.reserved_cpu + _EPSILON:
            raise ValueError("Cannot release more CPU than is reserved.")
        if memory_gb > self.reserved_memory_gb + _EPSILON:
            raise ValueError("Cannot release more memory than is reserved.")
        self.reserved_cpu = max(0.0, self.reserved_cpu - cpu)
        self.reserved_memory_gb = max(0.0, self.reserved_memory_gb - memory_gb)


@dataclass(frozen=True)
class Task:
    """A validated workload request owned by one simulated tenant."""

    task_id: str
    tenant_id: str
    cpu_required: float
    memory_required_gb: float
    latency_sensitivity: LatencySensitivity | str

    def __post_init__(self) -> None:
        _require_name(self.task_id, "task_id")
        _require_name(self.tenant_id, "tenant_id")
        _require_positive(self.cpu_required, "cpu_required")
        _require_positive(self.memory_required_gb, "memory_required_gb")
        try:
            sensitivity = LatencySensitivity(self.latency_sensitivity)
        except ValueError as exc:
            raise ValueError("latency_sensitivity must be low, medium, or high.") from exc
        object.__setattr__(self, "latency_sensitivity", sensitivity)


@dataclass(frozen=True)
class VM:
    """An in-memory VM record; it does not create a real virtual machine."""

    vm_id: str
    host_node_id: str
    allocated_cpu: float
    allocated_memory_gb: float
    status: VMStatus = VMStatus.RUNNING

    def __post_init__(self) -> None:
        _require_name(self.vm_id, "vm_id")
        _require_name(self.host_node_id, "host_node_id")
        _require_positive(self.allocated_cpu, "allocated_cpu")
        _require_positive(self.allocated_memory_gb, "allocated_memory_gb")
        try:
            object.__setattr__(self, "status", VMStatus(self.status))
        except ValueError as exc:
            raise ValueError("status must be running or stopped.") from exc


@dataclass(frozen=True)
class PlacementResult:
    """Per-task placement outcome, suitable for tenant-protected storage."""

    task: Task
    policy: PlacementPolicy
    status: PlacementStatus
    node_id: str | None
    simulated_latency_ms: float | None
    projected_cpu_utilization: float | None
    projected_memory_utilization: float | None
    rejection_reason: str | None = None


def create_default_nodes() -> list[Node]:
    """Create one configurable-by-caller default node of each tier."""
    return [
        Node("edge-1", NodeType.EDGE, cpu_capacity=8, memory_capacity_gb=8, base_latency_ms=5),
        Node("fog-1", NodeType.FOG, cpu_capacity=16, memory_capacity_gb=24, base_latency_ms=20),
        Node("cloud-1", NodeType.CLOUD, cpu_capacity=64, memory_capacity_gb=64, base_latency_ms=50),
    ]
