"""ATLAS Client Adapter Layer.

This package contains all external client adapters for the ATLAS platform.
Adapters translate external execution environments into calls on the public
Atlas SDK. They are presentation and transport layers only.

Each adapter:
- Imports exclusively from ``atlas``
- Never imports from ``engine``
- Handles only its own rendering and transport concerns
"""
