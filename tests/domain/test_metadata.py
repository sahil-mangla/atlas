"""Tests for the ArtifactMetadata model."""

from datetime import UTC, datetime

from engine.domain.metadata import ArtifactMetadata, ArtifactStatus


def test_artifact_metadata_creation() -> None:
    metadata = ArtifactMetadata()

    assert metadata.id is not None
    assert metadata.version == 1
    assert isinstance(metadata.created_at, datetime)
    assert metadata.created_at.tzinfo == UTC
    assert metadata.created_by == "system"
    assert metadata.status == ArtifactStatus.DRAFT

    # Test explicit values
    custom_time = datetime(2025, 1, 1, tzinfo=UTC)
    metadata_custom = ArtifactMetadata(
        version=2,
        created_at=custom_time,
        created_by="agent",
        status=ArtifactStatus.APPROVED,
    )

    assert metadata_custom.version == 2
    assert metadata_custom.created_at == custom_time
    assert metadata_custom.created_by == "agent"
    assert metadata_custom.status == ArtifactStatus.APPROVED
