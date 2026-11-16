"""Immutable leaf components. Components never construct views."""

from pydantic import BaseModel, ConfigDict


class Component(BaseModel):
    model_config = ConfigDict(frozen=True)


class StatusBadge(Component):
    label: str
    positive: bool


class Metric(Component):
    label: str
    value: int | float | str


class Section(Component):
    title: str
    body: str
