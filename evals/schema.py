"""Typed schema for evals/tasks/*.yaml -- see benchmark.yaml's header comment
for the human-readable field-by-field spec this mirrors.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Outcome = Literal["success", "error", "validation_error"]
Category = Literal[
    "tool_selection",
    "schema_correctness",
    "multi_step",
    "error_handling",
    "hallucination_check",
]
Adapter = Literal["cli", "mcp", "ide", "rest", "ai"]


class CheckSpec(BaseModel):
    """One machine-checkable assertion against a step's response.

    Exactly one of ``equals`` / ``non_empty`` / ``type`` must be provided --
    they are different assertion kinds, not fields with independent
    defaults.
    """

    model_config = ConfigDict(extra="forbid")

    field: str
    equals: Any = None
    non_empty: bool | None = None
    type: str | None = None

    @model_validator(mode="after")
    def _exactly_one_assertion_kind(self) -> CheckSpec:
        provided = self.model_fields_set & {"equals", "non_empty", "type"}
        if len(provided) != 1:
            raise ValueError(
                f"Check on {self.field!r} must set exactly one of "
                f"equals/non_empty/type, got: {sorted(provided)}"
            )
        return self


class CommandSpec(BaseModel):
    """A Command to construct, by registry type name, plus its kwargs."""

    model_config = ConfigDict(extra="forbid")

    type: str
    fields: dict[str, Any] = Field(default_factory=dict)


class InputSpec(BaseModel):
    """Wraps a single-step task's command -- matches `steps[].command`'s
    shape (a sibling of `expected`, not `expected` itself)."""

    model_config = ConfigDict(extra="forbid")

    command: CommandSpec


class StepExpected(BaseModel):
    """Expected outcome for one step. Omitted optional fields mean "no
    assertion for this field" -- distinguished from an explicit `null` via
    ``model_fields_set``, since e.g. ``capability: null`` is itself a real,
    meaningful assertion (the unrecognized-command-type case)."""

    model_config = ConfigDict(extra="forbid")

    outcome: Outcome
    capability: str | None = None
    ai_provider: str | None = None
    error_code: str | None = None
    result_type: str | None = None
    checks: list[CheckSpec] = Field(default_factory=list)

    def is_asserted(self, field_name: str) -> bool:
        """Whether ``field_name`` was explicitly provided (vs. defaulted)."""
        return field_name in self.model_fields_set


class StepSpec(BaseModel):
    """One Command in a task, with optional variable capture and AI stubbing."""

    model_config = ConfigDict(extra="forbid")

    command: CommandSpec
    capture: dict[str, str] = Field(default_factory=dict)
    ai_response: str | None = None
    expected: StepExpected


class TaskSpec(BaseModel):
    """One benchmark task: either a single `input` step or an ordered `steps` list."""

    model_config = ConfigDict(extra="forbid")

    task_id: str
    description: str
    adapter: Adapter
    category: Category
    input: InputSpec | None = None
    expected: StepExpected | None = None
    steps: list[StepSpec] | None = None

    @model_validator(mode="after")
    def _exactly_one_shape(self) -> TaskSpec:
        has_input = self.input is not None
        has_steps = self.steps is not None and len(self.steps) > 0
        if has_input == has_steps:
            raise ValueError(
                f"Task {self.task_id!r} must set exactly one of "
                f"input(+expected) / steps"
            )
        if has_input and self.expected is None:
            raise ValueError(f"Task {self.task_id!r} has `input` but no `expected`")
        return self

    def as_steps(self) -> list[StepSpec]:
        """Normalize both task shapes into a uniform list of steps."""
        if self.steps is not None:
            return self.steps
        assert self.input is not None and self.expected is not None
        return [StepSpec(command=self.input.command, expected=self.expected)]


class TaskFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tasks: list[TaskSpec]
