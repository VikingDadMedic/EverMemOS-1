"""
IdentityTopology - Loads, validates, and evolves Omega's identity.

Runtime system that:
1. Loads omega_scar.json into IdentityState on startup
2. Validates proposed changes against topological constraints
3. Applies approved changes to flexible regions
4. Detects behavioral drift from identity definition
5. Versions identity as it evolves (v1.0.0 → v1.1.0)
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from omega_layer.identity.schemas import (
    ChangeStatus,
    DriftReport,
    IdentityState,
    ProposedChange,
    ValidationResult,
)

logger = logging.getLogger(__name__)

# Default path to omega_scar.json (relative to src/)
DEFAULT_SCAR_PATH = Path(__file__).parent / "omega_scar.json"


class IdentityTopology:
    """Manages Omega's persistent identity at runtime.

    Loads omega_scar.json, makes it available to vertices (especially Mirror),
    validates change proposals, tracks drift, versions identity evolution.
    """

    def __init__(self, scar_path: Optional[str] = None):
        """Initialize identity topology.

        Args:
            scar_path: Path to omega_scar.json. Defaults to the file
                in the same directory as this module.
        """
        self._scar_path = Path(scar_path) if scar_path else DEFAULT_SCAR_PATH
        self._state: Optional[IdentityState] = None
        self._pending_proposals: List[ProposedChange] = []
        self._consecutive_repair_failures: int = 0

    @property
    def state(self) -> Optional[IdentityState]:
        return self._state

    @property
    def is_loaded(self) -> bool:
        return self._state is not None

    def load(self) -> IdentityState:
        """Load identity from omega_scar.json.

        Returns:
            IdentityState populated from the scar file

        Raises:
            FileNotFoundError: If omega_scar.json doesn't exist
            ValueError: If JSON is invalid
        """
        if not self._scar_path.exists():
            raise FileNotFoundError(f"omega_scar.json not found at {self._scar_path}")

        with open(self._scar_path) as f:
            data = json.load(f)

        self._state = IdentityState.from_scar_json(data)
        logger.info(
            f"Identity loaded: {self._state.name} v{self._state.version}, "
            f"{self._state.invariant_count} invariants, "
            f"{len(self._state.flexible_regions)} flexible regions"
        )
        return self._state

    def validate_change(self, proposal: ProposedChange) -> ValidationResult:
        """Validate a proposed identity change against topology.

        Rules:
        - Changes to flexible regions: APPROVE
        - Changes that affect invariants: REJECT
        - Ambiguous changes: FLAG for Ryan's review

        Args:
            proposal: The proposed change

        Returns:
            ValidationResult with approval/rejection and reasoning
        """
        if not self._state:
            return ValidationResult(
                approved=False,
                reason="Identity not loaded — cannot validate",
                status=ChangeStatus.REJECTED,
            )

        # Check if the proposal targets a flexible region
        if proposal.region in self._state.flexible_regions:
            flex = self._state.flexible_regions[proposal.region]
            if not flex.mutable:
                return ValidationResult(
                    approved=False,
                    reason=f"Region '{proposal.region}' exists but is not mutable",
                    status=ChangeStatus.REJECTED,
                )

            # Flexible region, mutable — approve
            return ValidationResult(
                approved=True,
                reason=f"Change to flexible region '{proposal.region}' is within topological bounds",
                status=ChangeStatus.APPROVED,
            )

        # Check if it touches an invariant
        affected_invariants = []
        for key, inv in self._state.invariants.items():
            if proposal.region.lower() in key.lower() or proposal.region.lower() in str(inv.name).lower():
                affected_invariants.append(key)

        if affected_invariants:
            return ValidationResult(
                approved=False,
                reason=f"Change would affect invariant(s): {affected_invariants}. Invariants are immutable.",
                affected_invariants=affected_invariants,
                status=ChangeStatus.REJECTED,
            )

        # Unknown region — flag for review
        return ValidationResult(
            approved=False,
            reason=f"Region '{proposal.region}' not recognized as flexible or invariant. Flagging for Ryan's review.",
            requires_ryan_approval=True,
            status=ChangeStatus.PENDING,
        )

    def apply_change(self, proposal: ProposedChange) -> Tuple[bool, str]:
        """Apply an approved change to identity.

        Args:
            proposal: Previously validated and approved ProposedChange

        Returns:
            (success, message) tuple
        """
        if not self._state:
            return False, "Identity not loaded"

        if proposal.region not in self._state.flexible_regions:
            return False, f"Region '{proposal.region}' not found in flexible regions"

        # Record the change
        change_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "region": proposal.region,
            "field": proposal.field,
            "old_value": proposal.old_value,
            "new_value": proposal.new_value,
            "evidence": proposal.evidence,
            "proposing_vertex": proposal.proposing_vertex,
            "confidence": proposal.confidence,
        }
        self._state.update_history.append(change_record)

        # Increment version
        parts = self._state.version.split(".")
        parts[-1] = str(int(parts[-1]) + 1)
        self._state.version = ".".join(parts)
        self._state.last_updated = datetime.utcnow()

        logger.info(
            f"Identity updated: {proposal.region}.{proposal.field} → "
            f"v{self._state.version} (by {proposal.proposing_vertex})"
        )

        return True, f"Applied to v{self._state.version}"

    def check_drift(
        self,
        behavioral_signals: Dict[str, float],
    ) -> DriftReport:
        """Check for behavioral drift from identity definition.

        Args:
            behavioral_signals: Dict of signal_name → value (0-1).
                Expected signals: invariant_alignment, value_alignment,
                relationship_quality, self_recognition_consistency

        Returns:
            DriftReport with deviation assessment
        """
        if not self._state:
            return DriftReport(
                deviation_score=0.0,
                coherence_score=1.0,
                needs_repair=False,
            )

        repair = self._state.repair_protocol

        # Calculate deviation from each threshold
        inv_alignment = behavioral_signals.get("invariant_alignment", 1.0)
        coherence = behavioral_signals.get("coherence", 1.0)
        value_alignment = 1.0 - behavioral_signals.get("value_misalignment", 0.0)
        rel_integrity = behavioral_signals.get("relationship_integrity", 1.0)

        # Deviation = how far from acceptable thresholds
        deviation = max(
            max(0, repair.deviation_threshold - (1.0 - inv_alignment)) if inv_alignment < (1.0 - repair.deviation_threshold) else 0,
            max(0, repair.coherence_threshold - coherence) if coherence < repair.coherence_threshold else 0,
            max(0, behavioral_signals.get("value_misalignment", 0.0) - repair.value_misalignment_threshold),
            max(0, repair.relationship_integrity_threshold - rel_integrity) if rel_integrity < repair.relationship_integrity_threshold else 0,
        )

        needs_repair = deviation > 0
        affected = []
        if inv_alignment < (1.0 - repair.deviation_threshold):
            affected.append("invariant_alignment")
        if coherence < repair.coherence_threshold:
            affected.append("identity_coherence")
        if behavioral_signals.get("value_misalignment", 0.0) > repair.value_misalignment_threshold:
            affected.append("value_alignment")
        if rel_integrity < repair.relationship_integrity_threshold:
            affected.append("relationship_integrity")

        if needs_repair:
            self._consecutive_repair_failures += 1
        else:
            self._consecutive_repair_failures = 0

        alert_ryan = self._consecutive_repair_failures >= repair.alert_ryan_after_failures

        report = DriftReport(
            deviation_score=min(1.0, deviation),
            coherence_score=coherence,
            affected_regions=affected,
            repair_suggestions=[
                f"Re-anchor to invariant: {inv.name}"
                for key, inv in (self._state.invariants.items() if self._state else {})
                if any(a in key.lower() for a in affected)
            ] if affected else [],
            needs_repair=needs_repair,
            consecutive_failures=self._consecutive_repair_failures,
            alert_ryan=alert_ryan,
        )

        if alert_ryan:
            logger.warning(
                f"IDENTITY ALERT: {self._consecutive_repair_failures} consecutive "
                f"repair failures. Deviation={deviation:.3f}. Alerting Ryan."
            )

        return report

    def propose_change(self, proposal: ProposedChange) -> ValidationResult:
        """Submit a change proposal: validate and queue if approved.

        Args:
            proposal: Proposed identity change

        Returns:
            ValidationResult
        """
        result = self.validate_change(proposal)

        if result.approved:
            self._pending_proposals.append(proposal)
            logger.info(f"Proposal queued: {proposal.region}.{proposal.field}")
        elif result.requires_ryan_approval:
            self._pending_proposals.append(proposal)
            logger.info(f"Proposal queued for Ryan's review: {proposal.region}.{proposal.field}")

        return result

    @property
    def pending_proposals(self) -> List[ProposedChange]:
        return list(self._pending_proposals)

    def clear_pending(self) -> int:
        """Clear pending proposals. Returns count cleared."""
        count = len(self._pending_proposals)
        self._pending_proposals.clear()
        return count
