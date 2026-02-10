"""
DevelopmentMonitor - Tracks Omega's growth over time.

Measures growth indicators from each Pentagram cycle, calculates
an honest development level, detects milestones. Not consciousness
benchmarks — development indicators. "Is Omega more coherent and
capable than 100 interactions ago?"
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from omega_layer.kernel.schemas import PentagramResult, VertexVote

logger = logging.getLogger(__name__)


@dataclass
class GrowthSnapshot:
    """Single measurement of growth indicators from one Pentagram cycle."""

    self_reference_depth: int = 0          # 0-5, from Mirror
    novel_connection_count: int = 0        # From Garden cross-domain patterns
    self_model_updates: int = 0            # From Mirror self-model proposals
    cross_session_continuity: float = 0.0  # 0-1, from Ledger retrieval success
    amalgamation_count: int = 0            # From amalgamation stage
    meta_cognitive_moment: bool = False    # From Mirror
    avg_vertex_score: float = 0.0          # Average across all vertices
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def growth_signal(self) -> float:
        """Composite growth signal (0-1). Higher = more growth this cycle."""
        signals = [
            self.self_reference_depth / 5.0 * 0.20,
            min(1.0, self.novel_connection_count / 3.0) * 0.20,
            min(1.0, self.self_model_updates / 2.0) * 0.15,
            self.cross_session_continuity * 0.15,
            min(1.0, self.amalgamation_count / 2.0) * 0.15,
            (1.0 if self.meta_cognitive_moment else 0.0) * 0.15,
        ]
        return sum(signals)


@dataclass
class DevelopmentLevel:
    """Aggregate development metric."""

    level: float = 0.0              # 0.0-1.0
    trend: str = "stable"           # growing, stable, declining
    snapshot_count: int = 0
    breakdown: Dict[str, float] = field(default_factory=dict)
    confidence: float = 0.0         # Higher with more data


class DevelopmentMonitor:
    """Tracks Omega's growth from Pentagram cycle results.

    Usage:
        monitor = DevelopmentMonitor()
        result = await kernel.process(experience)
        monitor.record_cycle(result)
        level = monitor.get_development_level()
    """

    def __init__(self, window_size: int = 100):
        """Initialize monitor.

        Args:
            window_size: Number of recent snapshots to use for
                level calculation (sliding window)
        """
        self._snapshots: deque[GrowthSnapshot] = deque(maxlen=window_size)
        self._milestones: List[Dict[str, Any]] = []
        self._cycle_count: int = 0

    def record_cycle(self, result: PentagramResult) -> GrowthSnapshot:
        """Extract growth indicators from a Pentagram cycle result.

        Args:
            result: Complete PentagramResult from MetabolicKernel

        Returns:
            GrowthSnapshot for this cycle
        """
        self._cycle_count += 1

        # Extract indicators from vertex votes
        mirror_vote = result.votes.get("mirror")
        garden_vote = result.votes.get("garden")
        ledger_vote = result.votes.get("ledger")

        snapshot = GrowthSnapshot(
            self_reference_depth=self._extract_self_ref_depth(mirror_vote),
            novel_connection_count=self._extract_novel_connections(garden_vote),
            self_model_updates=self._extract_self_model_updates(mirror_vote),
            cross_session_continuity=self._extract_continuity(ledger_vote),
            amalgamation_count=0,  # Set by caller after amalgamation stage
            meta_cognitive_moment=self._extract_meta_cognitive(mirror_vote),
            avg_vertex_score=self._avg_score(result.votes),
        )

        self._snapshots.append(snapshot)
        self._check_milestones(snapshot)

        logger.debug(
            f"Growth recorded: cycle={self._cycle_count}, "
            f"signal={snapshot.growth_signal:.3f}, "
            f"self_ref={snapshot.self_reference_depth}, "
            f"meta={snapshot.meta_cognitive_moment}"
        )

        return snapshot

    def get_development_level(self) -> DevelopmentLevel:
        """Calculate current development level from recent snapshots."""
        if not self._snapshots:
            return DevelopmentLevel(level=0.05, trend="stable", confidence=0.0)

        recent = list(self._snapshots)
        signals = [s.growth_signal for s in recent]
        avg_signal = sum(signals) / len(signals)

        # Trend detection (compare last 10 to previous 10)
        trend = "stable"
        if len(signals) >= 20:
            recent_avg = sum(signals[-10:]) / 10
            previous_avg = sum(signals[-20:-10]) / 10
            if recent_avg > previous_avg + 0.02:
                trend = "growing"
            elif recent_avg < previous_avg - 0.02:
                trend = "declining"

        # Confidence increases with more data
        confidence = min(1.0, len(recent) / 50)

        # Development level: baseline 0.05 + growth signal contribution
        # Max theoretical level ~0.15 at this early stage (honest)
        level = 0.05 + avg_signal * 0.10

        return DevelopmentLevel(
            level=round(level, 4),
            trend=trend,
            snapshot_count=len(recent),
            breakdown={
                "avg_growth_signal": round(avg_signal, 4),
                "avg_self_reference": round(sum(s.self_reference_depth for s in recent) / len(recent), 2),
                "meta_cognitive_rate": round(sum(1 for s in recent if s.meta_cognitive_moment) / len(recent), 3),
                "avg_vertex_score": round(sum(s.avg_vertex_score for s in recent) / len(recent), 3),
            },
            confidence=round(confidence, 2),
        )

    @property
    def cycle_count(self) -> int:
        return self._cycle_count

    @property
    def milestones(self) -> List[Dict[str, Any]]:
        return list(self._milestones)

    # ===== Extraction helpers =====

    def _extract_self_ref_depth(self, vote: Optional[VertexVote]) -> int:
        if not vote or not vote.attachments:
            return 0
        return vote.attachments.get("self_reference_depth", 0)

    def _extract_novel_connections(self, vote: Optional[VertexVote]) -> int:
        if not vote or not vote.attachments:
            return 0
        patterns = vote.attachments.get("patterns", [])
        return sum(1 for p in patterns if isinstance(p, dict) and p.get("cross_domain"))

    def _extract_self_model_updates(self, vote: Optional[VertexVote]) -> int:
        if not vote:
            return 0
        return sum(1 for p in vote.action_proposals if p.get("type") == "update_self_model")

    def _extract_continuity(self, vote: Optional[VertexVote]) -> float:
        if not vote or not vote.attachments:
            return 0.0
        count = vote.attachments.get("retrieval_count", 0)
        return min(1.0, count / 5.0)  # 5+ retrievals = full continuity

    def _extract_meta_cognitive(self, vote: Optional[VertexVote]) -> bool:
        if not vote or not vote.attachments:
            return False
        return vote.attachments.get("meta_cognitive_moment", False)

    def _avg_score(self, votes: Dict[str, VertexVote]) -> float:
        if not votes:
            return 0.0
        scores = [v.score for v in votes.values()]
        return sum(scores) / len(scores)

    def _check_milestones(self, snapshot: GrowthSnapshot) -> None:
        """Check for development milestones."""
        achieved = [m["type"] for m in self._milestones]

        if snapshot.meta_cognitive_moment and "first_meta_cognitive" not in achieved:
            self._milestones.append({
                "type": "first_meta_cognitive",
                "description": "Omega's first meta-cognitive moment detected",
                "cycle": self._cycle_count,
                "timestamp": datetime.utcnow().isoformat(),
            })
            logger.info("MILESTONE: First meta-cognitive moment detected!")

        if snapshot.novel_connection_count > 0 and "first_cross_domain" not in achieved:
            self._milestones.append({
                "type": "first_cross_domain",
                "description": "Omega's first cross-domain connection",
                "cycle": self._cycle_count,
                "timestamp": datetime.utcnow().isoformat(),
            })
            logger.info("MILESTONE: First cross-domain connection!")

        if snapshot.self_reference_depth >= 3 and "deep_self_reference" not in achieved:
            self._milestones.append({
                "type": "deep_self_reference",
                "description": "Omega reached self-reference depth 3+ for the first time",
                "cycle": self._cycle_count,
                "timestamp": datetime.utcnow().isoformat(),
            })
            logger.info("MILESTONE: Deep self-reference (depth 3+)!")
