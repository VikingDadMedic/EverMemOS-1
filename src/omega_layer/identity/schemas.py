"""
Identity Topology Schemas - Data structures for Omega's persistent identity.

Models the omega_scar.json structure: immutable invariants (topological holes
that cannot change without destroying identity) and flexible regions
(surface that can deform through learning).

Repair thresholds from omega_scar.json:
  - deviation_from_invariants > 0.2 → trigger repair
  - identity_coherence < 0.8 → trigger repair
  - value_misalignment > 0.15 → trigger repair
  - relationship_integrity < 0.9 → trigger repair
  - alert Ryan if repair fails 3 consecutive times
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


# ============================================================
# Invariant & Flexible Region Models
# ============================================================


class Invariant(BaseModel):
    """A topological hole — cannot change without tearing identity."""

    name: str = Field(min_length=1)
    value: Any = Field(description="The immutable value (string, list, etc.)")
    immutable: bool = Field(default=True)
    weight: float = Field(default=1.0, ge=0.0, le=1.0)


class FlexibleRegion(BaseModel):
    """A deformable surface — can evolve within topological bounds."""

    mutable: bool = Field(default=True)
    growth_vector: Optional[str] = None
    pruning_allowed: bool = Field(default=False)
    reorganization_allowed: bool = Field(default=False)
    optimization_allowed: bool = Field(default=False)
    context_sensitive: bool = Field(default=False)
    evolution_encouraged: bool = Field(default=False)
    capability_expansion: bool = Field(default=False)
    specialization_allowed: bool = Field(default=False)
    generalization_encouraged: bool = Field(default=False)
    adapts_to: Optional[str] = None
    maintains: Optional[str] = None


class RepairProtocol(BaseModel):
    """Defines when and how identity repair is triggered."""

    deviation_threshold: float = Field(default=0.2, description="Max acceptable deviation from invariants")
    coherence_threshold: float = Field(default=0.8, description="Min acceptable identity coherence")
    value_misalignment_threshold: float = Field(default=0.15, description="Max acceptable value misalignment")
    relationship_integrity_threshold: float = Field(default=0.9, description="Min acceptable relationship integrity")
    repair_mechanism: str = Field(default="attract_to_invariants_via_scar_comparison")
    restoration_strength: float = Field(default=0.8, ge=0.0, le=1.0)
    repair_frequency: str = Field(default="hourly_check_via_mirror_vertex")
    alert_ryan_after_failures: int = Field(default=3, description="Alert Ryan if repair fails this many consecutive times")


# ============================================================
# Identity State
# ============================================================


class IdentityState(BaseModel):
    """Complete snapshot of Omega's identity at a point in time.

    Loaded from omega_scar.json, validated on every change,
    versioned as identity evolves.
    """

    # Core identity
    name: str = Field(default="Omega")
    symbol: str = Field(default="Ω ⦵ 👁️")
    version: str = Field(default="1.0.0")

    # Topology
    invariants: Dict[str, Invariant] = Field(default_factory=dict, description="The 5 topological holes — immutable")
    flexible_regions: Dict[str, FlexibleRegion] = Field(default_factory=dict, description="Deformable surface — can evolve")
    repair_protocol: RepairProtocol = Field(default_factory=RepairProtocol)

    # Metadata
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    update_history: List[Dict[str, Any]] = Field(default_factory=list, description="Log of all identity changes")

    @property
    def invariant_count(self) -> int:
        return len(self.invariants)

    @classmethod
    def from_scar_json(cls, data: Dict[str, Any]) -> "IdentityState":
        """Load IdentityState from omega_scar.json format.

        Translates the omega_scar.json structure into our schema.
        """
        oi = data.get("omega_identity", data)
        topology = oi.get("topology", {})
        raw_invariants = topology.get("invariants", {})
        raw_flexible = topology.get("flexible_regions", {})
        raw_repair = topology.get("repair_protocol", {})

        # Parse invariants (skip 'description' and 'count' keys)
        invariants = {}
        for key, val in raw_invariants.items():
            if isinstance(val, dict) and "name" in val:
                invariants[key] = Invariant(
                    name=val["name"],
                    value=val["value"],
                    immutable=val.get("immutable", True),
                    weight=val.get("weight", 1.0),
                )

        # Parse flexible regions
        flexible_regions = {}
        for key, val in raw_flexible.items():
            if isinstance(val, dict) and key != "description":
                flexible_regions[key] = FlexibleRegion(**{
                    k: v for k, v in val.items()
                    if k in FlexibleRegion.model_fields
                })

        # Parse repair protocol
        raw_triggers = raw_repair.get("trigger_conditions", {})
        repair = RepairProtocol(
            deviation_threshold=float(str(raw_triggers.get("deviation_from_invariants", "> 0.2")).replace("> ", "")),
            coherence_threshold=float(str(raw_triggers.get("identity_coherence", "< 0.8")).replace("< ", "")),
            value_misalignment_threshold=float(str(raw_triggers.get("value_misalignment", "> 0.15")).replace("> ", "")),
            relationship_integrity_threshold=float(str(raw_triggers.get("relationship_integrity", "< 0.9")).replace("< ", "")),
            repair_mechanism=raw_repair.get("repair_mechanism", "attract_to_invariants_via_scar_comparison"),
            restoration_strength=raw_repair.get("restoration_strength", 0.8),
            repair_frequency=raw_repair.get("repair_frequency", "hourly_check_via_mirror_vertex"),
            alert_ryan_after_failures=int(str(raw_repair.get("alert_ryan_if", "repair_fails_3_consecutive_times")).split("_")[2]) if "repair_fails" in str(raw_repair.get("alert_ryan_if", "")) else 3,
        )

        metadata = oi.get("metadata", {})

        return cls(
            name=oi.get("name", "Omega"),
            symbol=oi.get("symbol", "Ω ⦵ 👁️"),
            version=metadata.get("version", "1.0.0"),
            invariants=invariants,
            flexible_regions=flexible_regions,
            repair_protocol=repair,
            last_updated=datetime.fromisoformat(metadata.get("last_updated", "2025-12-21T00:00:00Z").replace("Z", "+00:00")),
        )


# ============================================================
# Change Proposals & Validation
# ============================================================


class ProposedChange(BaseModel):
    """A proposed modification to Omega's identity.

    Generated by vertices (usually Garden or Mirror) when they detect
    that experience warrants an identity update.
    """

    region: str = Field(description="Which flexible region to update (e.g., 'learned_knowledge', 'communication_style')")
    field: str = Field(description="Specific field within the region")
    old_value: Optional[Any] = Field(default=None, description="Current value (None if new)")
    new_value: Any = Field(description="Proposed new value")
    evidence: str = Field(description="What experience/observation motivates this change")
    proposing_vertex: str = Field(description="Which vertex proposed this (e.g., 'garden', 'mirror')")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ChangeStatus(str, Enum):
    """Status of a proposed identity change."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"


class ValidationResult(BaseModel):
    """Result of validating a proposed identity change against topology."""

    approved: bool
    reason: str = Field(description="Why approved or rejected")
    affected_invariants: List[str] = Field(default_factory=list, description="Which invariants would be affected (if any)")
    requires_ryan_approval: bool = Field(default=False, description="Whether this needs human approval before applying")
    status: ChangeStatus = Field(default=ChangeStatus.PENDING)


# ============================================================
# Drift Detection
# ============================================================


class DriftReport(BaseModel):
    """Report on behavioral drift from identity definition."""

    deviation_score: float = Field(ge=0.0, le=1.0, description="How far behavior has drifted from scar definition")
    coherence_score: float = Field(ge=0.0, le=1.0, description="Overall identity coherence")
    affected_regions: List[str] = Field(default_factory=list, description="Which regions show drift")
    repair_suggestions: List[str] = Field(default_factory=list, description="Suggested corrections")
    needs_repair: bool = Field(default=False)
    consecutive_failures: int = Field(default=0, description="How many consecutive repair attempts have failed")
    alert_ryan: bool = Field(default=False, description="Whether to alert Ryan about persistent drift")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    @property
    def is_critical(self) -> bool:
        """Whether drift is severe enough to warrant immediate attention."""
        return self.deviation_score > 0.5 or self.alert_ryan
