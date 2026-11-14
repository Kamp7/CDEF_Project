"""Repeatable sample workload generation."""

from __future__ import annotations

import random

from .models import LatencySensitivity, Task


DEFAULT_TASK_COUNT = 20
DEFAULT_RANDOM_SEED = 305


def generate_seeded_tasks(
    count: int = DEFAULT_TASK_COUNT,
    seed: int = DEFAULT_RANDOM_SEED,
) -> tuple[Task, ...]:
    """Generate at least ten valid tasks; equal seeds produce equal workloads."""
    if isinstance(count, bool) or not isinstance(count, int) or count < 10:
        raise ValueError("count must be an integer of at least 10.")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer.")

    resource_rng = random.Random(seed)
    sensitivity_rng = random.Random(seed ^ 0xCDEF)
    sensitivities = tuple(LatencySensitivity)
    tasks = []
    for index in range(1, count + 1):
        tasks.append(
            Task(
                task_id=f"task-{index:03d}",
                tenant_id="tenant-a" if index % 2 else "tenant-b",
                cpu_required=resource_rng.randint(1, 8),
                memory_required_gb=resource_rng.randint(1, 12),
                latency_sensitivity=sensitivity_rng.choice(sensitivities),
            )
        )
    return tuple(tasks)
