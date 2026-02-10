"""
StandaloneDriftDetector - Scheduled identity drift checking.

Aggregates behavioral signals from recent PentagramResults and
checks for drift from omega_scar.json identity definition.
Can be called on schedule (hourly per scar spec) or on-demand.
"""

from __future__ import annotations

import logging
from collections import deque
from typing import Any, Dict, List, Optional

from omega_layer.identity.schemas import DriftReport
from omega_layer.identity.topology import IdentityTopology
from omega_layer.kernel.schemas import PentagramResult, VertexVote

logger = logging.getLogger(__name__)


class StandaloneDriftDetector:
    """Aggregates behavioral signals from Pentagram cycles for drift detection.

    Accumulates recent PentagramResults, extracts behavioral signals,
    and periodically checks against identity topology.

    Usage:
        detector = StandaloneDriftDetector(topology)
        detector.record_cycle(pentagram_result)
        report = detector.check_now()
    """

    def __init__(
        self,
        topology: IdentityTopology,
        window_size: int = 50,
    ):
        self._topology = topology
        self._recent_cycles: deque[PentagramResult] = deque(maxlen=window_size)
        self._check_count: int = 0

    def record_cycle(self, result: PentagramResult) -> None:
        """Record a Pentagram cycle for drift analysis."""
        self._recent_cycles.append(result)

    def check_now(self) -> DriftReport:
        """Run drift detection against accumulated behavioral signals.

        Returns:
            DriftReport with deviation assessment
        """
        self._check_count += 1
        signals = self._aggregate_signals()

        report = self._topology.check_drift(signals)

        if report.needs_repair:
            logger.warning(
                f"Drift detected (check #{self._check_count}): "
                f"deviation={report.deviation_score:.3f}, "
                f"affected={report.affected_regions}"
            )
        else:
            logger.debug(
                f"Drift check #{self._check_count}: healthy "
                f"(coherence={report.coherence_score:.3f})"
            )

        return report

    def _aggregate_signals(self) -> Dict[str, float]:
        """Aggregate behavioral signals from recent cycles.

        Extracts proxy measurements for:
        - invariant_alignment: Are responses consistent with core purpose?
        - coherence: Are vertex votes internally consistent?
        - value_misalignment: Do actions diverge from stated values?
        - relationship_integrity: Is interaction quality with Ryan maintained?
        """
        if not self._recent_cycles:
            return {
                "invariant_alignment": 1.0,
                "coherence": 1.0,
                "value_misalignment": 0.0,
                "relationship_integrity": 1.0,
            }

        cycles = list(self._recent_cycles)

        # Invariant alignment: proxy via Mirror vertex alignment scores
        mirror_alignments = []
        for c in cycles:
            mirror = c.votes.get("mirror")
            if mirror and mirror.attachments:
                alignment = mirror.attachments.get("identity_alignment", {})
                if isinstance(alignment, dict):
                    score = alignment.get("invariant_alignment", 1.0)
                    mirror_alignments.append(score if isinstance(score, (int, float)) else 1.0)

        # Coherence: low tension magnitude = high coherence
        avg_tension = 0.0
        tension_count = 0
        for c in cycles:
            for t in c.tensions:
                avg_tension += t.magnitude
                tension_count += 1
        if tension_count > 0:
            avg_tension /= tension_count
        coherence = 1.0 - avg_tension  # High tension = low coherence

        # Value misalignment: proxy via Compass goal alignment
        compass_alignments = []
        for c in cycles:
            compass = c.votes.get("compass")
            if compass and compass.attachments:
                goal = compass.attachments.get("goal_alignment", {})
                if isinstance(goal, dict):
                    score = goal.get("alignment_score", 1.0)
                    compass_alignments.append(score if isinstance(score, (int, float)) else 1.0)

        # Relationship integrity: proxy via Orchestra expression quality
        orchestra_scores = []
        for c in cycles:
            orchestra = c.votes.get("orchestra")
            if orchestra:
                orchestra_scores.append(orchestra.score)

        return {
            "invariant_alignment": (
                sum(mirror_alignments) / len(mirror_alignments)
                if mirror_alignments else 1.0
            ),
            "coherence": max(0.0, min(1.0, coherence)),
            "value_misalignment": (
                1.0 - (sum(compass_alignments) / len(compass_alignments))
                if compass_alignments else 0.0
            ),
            "relationship_integrity": (
                sum(orchestra_scores) / len(orchestra_scores)
                if orchestra_scores else 1.0
            ),
        }

    @property
    def cycle_count(self) -> int:
        return len(self._recent_cycles)

    @property
    def check_count(self) -> int:
        return self._check_count
