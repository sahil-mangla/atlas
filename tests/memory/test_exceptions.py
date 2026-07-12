"""Unit tests for the memory exceptions."""

from engine.memory.exceptions import (
    InvalidMemoryException,
    MemoryException,
    MemoryNotFoundException,
)


def test_memory_exception_hierarchy() -> None:
    assert issubclass(MemoryNotFoundException, MemoryException)
    assert issubclass(InvalidMemoryException, MemoryException)
    assert issubclass(MemoryException, Exception)


def test_memory_exceptions_instantiation() -> None:
    e = MemoryNotFoundException("test msg")
    assert str(e) == "test msg"
