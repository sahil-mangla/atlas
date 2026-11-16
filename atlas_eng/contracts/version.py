"""Platform API versioning for the ATLAS contract layer.

Governs compatibility between clients and the platform. Commands and Results
may only gain new optional fields with defaults within a major version;
removing a field, changing a field's type, or changing error-code semantics
requires a PLATFORM_API_VERSION major bump.
"""

#: Semver wire-contract version clients negotiate against.
PLATFORM_API_VERSION = "1.0.0"

#: Integer envelope-shape version; bumped only on breaking envelope changes
#: (i.e. RequestEnvelope/ResponseEnvelope gaining or losing required fields).
SCHEMA_VERSION = 1


def is_compatible(client_api_version: str) -> bool:
    """Return whether a client's declared API version is compatible.

    Same major version is always compatible -- minor/patch changes are
    additive-only by policy and never break an existing client.

    Args:
        client_api_version: The API version string a client declares.

    Returns:
        True if the client's major version matches the platform's.
    """
    return client_api_version.split(".", 1)[0] == PLATFORM_API_VERSION.split(".", 1)[0]
