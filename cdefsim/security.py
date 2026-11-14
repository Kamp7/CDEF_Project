"""Tenant-scoped access to protected task placement records."""

from __future__ import annotations

from .models import PlacementResult


class AccessDenied(PermissionError):
    """Raised without disclosing whether another tenant owns a task ID."""

    def __init__(self) -> None:
        super().__init__("Task record unavailable.")


class TenantTaskStore:
    def __init__(self) -> None:
        self._records: dict[str, PlacementResult] = {}

    def record(self, result: PlacementResult) -> None:
        if not isinstance(result, PlacementResult):
            raise TypeError("result must be a PlacementResult instance.")
        task_id = result.task.task_id
        if task_id in self._records:
            raise ValueError("A task record with this ID already exists.")
        self._records[task_id] = result

    def get(self, tenant_id: str, task_id: str) -> PlacementResult:
        result = self._records.get(task_id)
        if result is None or result.task.tenant_id != tenant_id:
            raise AccessDenied()
        return result

    def list_for(self, tenant_id: str) -> tuple[PlacementResult, ...]:
        return tuple(
            self._records[task_id]
            for task_id in sorted(self._records)
            if self._records[task_id].task.tenant_id == tenant_id
        )
