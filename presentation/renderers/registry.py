from typing import Any, Protocol

from presentation.renderers.contract import RenderContract
from presentation.renderers.result import RenderResult


class Renderer(Protocol):
    name: str

    def render(self, view: Any, contract: RenderContract) -> RenderResult: ...


class RendererRegistry:
    def __init__(self, renderers: tuple[Renderer, ...]) -> None:
        self._renderers = {renderer.name: renderer for renderer in renderers}

    def resolve(self, name: str) -> Renderer:
        try:
            return self._renderers[name]
        except KeyError as exc:
            raise ValueError(f"Unknown renderer: {name}") from exc
