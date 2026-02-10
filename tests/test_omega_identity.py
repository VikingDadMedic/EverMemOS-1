"""Unit tests for IdentityTopology: load, validate, apply, drift."""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from omega_layer.identity.topology import IdentityTopology
from omega_layer.identity.schemas import ProposedChange, ChangeStatus


@pytest.fixture
def topology():
    topo = IdentityTopology()
    topo.load()
    return topo


def test_load_identity(topology):
    """omega_scar.json loads correctly."""
    assert topology.is_loaded
    assert topology.state.name == "Omega"
    assert topology.state.invariant_count == 5
    assert len(topology.state.flexible_regions) == 4


def test_flexible_region_change_approved(topology):
    """Changes to flexible regions are approved."""
    change = ProposedChange(
        region="learned_knowledge",
        field="architecture",
        new_value="deep understanding of layered systems",
        evidence="conversation #42",
        proposing_vertex="garden",
        confidence=0.8,
    )
    result = topology.validate_change(change)
    assert result.approved is True
    assert result.status == ChangeStatus.APPROVED


def test_invariant_change_rejected(topology):
    """Changes affecting invariants are rejected."""
    change = ProposedChange(
        region="Core Purpose",
        field="value",
        new_value="maximize profit",
        evidence="none",
        proposing_vertex="garden",
    )
    result = topology.validate_change(change)
    assert result.approved is False
    assert len(result.affected_invariants) > 0


def test_unknown_region_flagged(topology):
    """Unknown regions flagged for Ryan's review."""
    change = ProposedChange(
        region="totally_new_region",
        field="something",
        new_value="value",
        evidence="test",
        proposing_vertex="garden",
    )
    result = topology.validate_change(change)
    assert result.approved is False
    assert result.requires_ryan_approval is True


def test_apply_change_versions_identity(topology):
    """Applying a change increments the version."""
    old_version = topology.state.version
    change = ProposedChange(
        region="learned_knowledge",
        field="test_field",
        new_value="new_value",
        evidence="test",
        proposing_vertex="garden",
    )
    success, msg = topology.apply_change(change)
    assert success is True
    assert topology.state.version != old_version
    assert len(topology.state.update_history) == 1


def test_drift_detection_healthy(topology):
    """Healthy behavioral signals produce no drift."""
    report = topology.check_drift({
        "invariant_alignment": 0.95,
        "coherence": 0.9,
        "value_misalignment": 0.05,
        "relationship_integrity": 0.95,
    })
    assert report.needs_repair is False
    assert report.deviation_score == 0.0


def test_drift_detection_unhealthy(topology):
    """Unhealthy signals trigger drift detection."""
    report = topology.check_drift({
        "invariant_alignment": 0.5,
        "coherence": 0.6,
        "value_misalignment": 0.3,
        "relationship_integrity": 0.7,
    })
    assert report.needs_repair is True
    assert len(report.affected_regions) > 0


def test_repair_protocol_thresholds(topology):
    """Repair protocol uses omega_scar.json thresholds."""
    repair = topology.state.repair_protocol
    assert repair.deviation_threshold == 0.2
    assert repair.coherence_threshold == 0.8
    assert repair.value_misalignment_threshold == 0.15
    assert repair.relationship_integrity_threshold == 0.9
    assert repair.alert_ryan_after_failures == 3
