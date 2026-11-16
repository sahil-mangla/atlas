"""Map installed module names back to the architecture's layer names.

Every layer now lives under the single ``atlas_eng`` import root, so a plain
prefix check can no longer tell the public SDK (``atlas_eng.commands``) from
the engine (``atlas_eng.engine.domain``). The boundary tests are written in
terms of the layers -- ``atlas`` (the SDK), ``engine``, ``clients``,
``presentation``, ``shared`` -- and use this to translate first.
"""

ROOT = "atlas_eng"
_LAYERS = ("engine", "clients", "presentation", "shared", "interfaces")


def layer_module(module: str) -> str:
    """Return ``module`` renamed into layer terms.

    ``atlas_eng.engine.ai`` -> ``engine.ai``; ``atlas_eng.commands`` ->
    ``atlas.commands``; ``atlas_eng`` -> ``atlas``; anything outside the
    package is returned unchanged.
    """
    if module == ROOT:
        return "atlas"
    prefix = ROOT + "."
    if not module.startswith(prefix):
        return module
    rest = module[len(prefix) :]
    head = rest.split(".", 1)[0]
    return rest if head in _LAYERS else f"atlas.{rest}"
