"""
Smoke test: Verify omega_layer package structure is importable.

This test ensures the directory structure and __init__.py files
are correctly set up without introducing import side effects.
"""

import sys
import os

# Ensure src/ is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def test_omega_layer_root_import():
    """Root omega_layer package imports without error."""
    import omega_layer

    assert omega_layer is not None


def test_omega_layer_subpackage_imports():
    """All omega_layer subpackages import without error."""
    from omega_layer import kernel
    from omega_layer import vertices
    from omega_layer import identity
    from omega_layer import development
    from omega_layer import corpus
    from omega_layer import extractors
    from omega_layer import prompts

    assert kernel is not None
    assert vertices is not None
    assert identity is not None
    assert development is not None
    assert corpus is not None
    assert extractors is not None
    assert prompts is not None


def test_omega_prompts_en_import():
    """English prompts subpackage imports without error."""
    from omega_layer.prompts import en

    assert en is not None


def test_omega_api_adapter_import():
    """Omega API adapter package imports without error."""
    from infra_layer.adapters.input.api import omega

    assert omega is not None


def test_omega_scar_json_exists():
    """omega_scar.json exists and is valid JSON."""
    import json

    scar_path = os.path.join(
        os.path.dirname(__file__), "..", "src", "omega_layer", "identity", "omega_scar.json"
    )
    assert os.path.exists(scar_path), f"omega_scar.json not found at {scar_path}"

    with open(scar_path) as f:
        data = json.load(f)

    # Verify critical structure
    assert "omega_identity" in data
    assert "topology" in data["omega_identity"]
    assert "invariants" in data["omega_identity"]["topology"]
    assert data["omega_identity"]["topology"]["invariants"]["count"] == 5


def test_existing_evermemos_unaffected():
    """Existing EverMemOS imports still work (no regression)."""
    # These imports should succeed — omega_layer doesn't break anything
    from api_specs.memory_types import MemoryType, RawDataType

    assert MemoryType.EPISODIC_MEMORY is not None
    assert RawDataType.CONVERSATION is not None
