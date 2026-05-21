"""Validation workflow domain models for CI scripts."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class GateResult:
    name: str
    passed: bool
    summary: str = ""
    code: int = 0

    def fail_message(self) -> str:
        return f"Gate [{self.name}] FAILED: {self.summary}"


@dataclass
class ValidationRun:
    run_id: str
    gates: list[GateResult] = field(default_factory=list)
    passed: bool = True

    def add_gate(self, result: GateResult) -> None:
        self.gates.append(result)
        if not result.passed:
            self.passed = False

    def failing_gates(self) -> list[GateResult]:
        return [g for g in self.gates if not g.passed]

    def summary_lines(self) -> list[str]:
        lines = [f"Validation run {self.run_id}"]
        lines.append(f"Overall: {'PASSED' if self.passed else 'FAILED'}")
        lines.append(f"Gates run: {len(self.gates)}")
        for g in self.gates:
            status = "PASS" if g.passed else "FAIL"
            lines.append(f"  [{status}] {g.name}: {g.summary}")
        return lines


@dataclass
class ThresholdCheck:
    name: str
    value: float
    threshold: float
    passed: bool

    def message(self) -> str:
        return f"{self.name}: {self.value:.3f} vs threshold {self.threshold:.3f}"


@dataclass
class EvalResult:
    run_id: str
    dataset_id: str
    metrics: dict[str, float]
    passed: bool = True
    failures: list[str] = field(default_factory=list)


@dataclass
class ReportStorageResult:
    bucket: str
    key: str
    stored: bool
    error: Optional[str] = None
