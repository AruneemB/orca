"""Tests that verify the orcanet package structure and importability."""

from __future__ import annotations

import importlib
import sys


def test_package_importable() -> None:
    """orcanet is importable without errors."""
    import orcanet  # noqa: F401


def test_version_attribute() -> None:
    """orcanet.__version__ is a non-empty string."""
    import orcanet

    assert isinstance(orcanet.__version__, str)
    assert orcanet.__version__


def test_submodule_transfer_importable() -> None:
    """orcanet.transfer sub-package is importable."""
    importlib.import_module("orcanet.transfer")


def test_submodule_embeddings_importable() -> None:
    """orcanet.embeddings sub-package is importable."""
    importlib.import_module("orcanet.embeddings")


def test_submodule_reasoning_importable() -> None:
    """orcanet.reasoning sub-package is importable."""
    importlib.import_module("orcanet.reasoning")


def test_submodule_reasoning_prompts_importable() -> None:
    """orcanet.reasoning.prompts sub-package is importable."""
    importlib.import_module("orcanet.reasoning.prompts")


def test_submodule_retrieval_importable() -> None:
    """orcanet.retrieval sub-package is importable."""
    importlib.import_module("orcanet.retrieval")


def test_submodule_api_importable() -> None:
    """orcanet.api sub-package is importable."""
    importlib.import_module("orcanet.api")


def test_no_submodule_cross_import_side_effects() -> None:
    """Importing all sub-packages does not leave unexpected names in sys.modules."""
    before = set(sys.modules.keys())
    for mod in [
        "orcanet",
        "orcanet.transfer",
        "orcanet.embeddings",
        "orcanet.reasoning",
        "orcanet.reasoning.prompts",
        "orcanet.retrieval",
        "orcanet.api",
    ]:
        importlib.import_module(mod)

    after = set(sys.modules.keys())
    new_mods = after - before
    # All new modules should be orcanet sub-modules or standard library
    non_orcanet = {m for m in new_mods if not m.startswith("orcanet")}
    assert not non_orcanet, f"Unexpected modules registered: {non_orcanet}"
