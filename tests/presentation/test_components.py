"""Component tests: immutability, renderer independence, no Atlas dependency."""

import pytest
from pydantic import ValidationError

from presentation.components import Metric, Section, StatusBadge


def test_status_badge_is_frozen() -> None:
    badge = StatusBadge(label="healthy", positive=True)
    with pytest.raises(ValidationError):
        badge.label = "unhealthy"


def test_metric_is_frozen() -> None:
    metric = Metric(label="Sources", value=3)
    with pytest.raises(ValidationError):
        metric.value = 4


def test_section_is_frozen() -> None:
    section = Section(title="Objective", body="Ship it")
    with pytest.raises(ValidationError):
        section.body = "Changed"


def test_metric_accepts_int_float_or_str_value() -> None:
    assert Metric(label="a", value=1).value == 1
    assert Metric(label="b", value=1.5).value == 1.5
    assert Metric(label="c", value="text").value == "text"


def test_components_module_has_no_atlas_or_engine_symbols() -> None:
    import presentation.components.models as mod

    source = mod.__file__
    assert source is not None
    with open(source) as f:
        content = f.read()
    assert "atlas" not in content.lower()
    assert "engine" not in content.lower()
