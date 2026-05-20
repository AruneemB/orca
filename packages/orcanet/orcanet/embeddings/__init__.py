"""Domain-invariant embedding modules."""

from __future__ import annotations

__all__ = ["CrossDomainEmbedder", "GradientReversalLayer", "TextTaskEmbedder"]


def __getattr__(name: str) -> object:
    if name == "CrossDomainEmbedder":
        from .cross_domain import CrossDomainEmbedder

        return CrossDomainEmbedder
    if name == "GradientReversalLayer":
        from .cross_domain import GradientReversalLayer

        return GradientReversalLayer
    if name == "TextTaskEmbedder":
        from .text_features import TextTaskEmbedder

        return TextTaskEmbedder
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
