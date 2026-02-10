"""
Omega Controller - REST endpoints for omega-mode interactions.

POST /api/v1/omega/process — Route through Pentagram cycle
GET  /api/v1/omega/development — Get current development level
GET  /api/v1/omega/identity — Get current identity state
GET  /api/v1/omega/identity/proposals — List pending proposals
POST /api/v1/omega/identity/proposals/{id}/approve — Approve proposal
"""

from __future__ import annotations

import json
import logging
import os
import time

from fastapi import HTTPException, Request as FastAPIRequest

from core.di.decorators import controller
from core.interface.controller.base_controller import BaseController, get, post
from core.constants.errors import ErrorStatus

logger = logging.getLogger(__name__)


@controller("omega_controller", primary=False)
class OmegaController(BaseController):
    """Omega-mode API endpoints."""

    def __init__(self):
        super().__init__(
            prefix="/api/v1/omega",
            tags=["Omega Controller"],
            default_auth="none",
        )
        self._kernel = None
        self._monitor = None
        self._identity = None
        logger.info("OmegaController initialized")

    def _get_kernel(self):
        """Lazy-init the MetabolicKernel with all vertices."""
        if self._kernel is None:
            from omega_layer.kernel.metabolic_kernel import MetabolicKernel
            from omega_layer.vertices.ledger_vertex import LedgerVertex
            from omega_layer.vertices.garden_vertex import GardenVertex
            from omega_layer.vertices.mirror_vertex import MirrorVertex
            from omega_layer.vertices.compass_vertex import CompassVertex
            from omega_layer.vertices.orchestra_vertex import OrchestraVertex
            from memory_layer.llm.llm_provider import LLMProvider

            # Create LLM provider for vertices
            llm = LLMProvider(
                provider_type=os.getenv("LLM_PROVIDER", "openai"),
                model=os.getenv("OMEGA_LLM_MODEL", os.getenv("LLM_MODEL", "gpt-4.1-mini")),
                base_url=os.getenv("LLM_BASE_URL"),
                api_key=os.getenv("LLM_API_KEY"),
                temperature=float(os.getenv("LLM_TEMPERATURE", "0.3")),
                max_tokens=int(os.getenv("LLM_MAX_TOKENS", "4096")),
            )

            # Assemble Pentagram
            self._kernel = MetabolicKernel(llm_provider=llm)

            ledger = LedgerVertex()
            garden = GardenVertex()
            garden.configure_llm(llm)
            mirror = MirrorVertex()
            mirror.configure_llm(llm)
            compass = CompassVertex()
            compass.configure_llm(llm)
            orchestra = OrchestraVertex()

            self._kernel.register_vertex(ledger)
            self._kernel.register_vertex(garden)
            self._kernel.register_vertex(mirror)
            self._kernel.register_vertex(compass)
            self._kernel.register_vertex(orchestra)

            logger.info(f"Pentagram assembled: {self._kernel.vertex_count} vertices")

        return self._kernel

    def _get_monitor(self):
        if self._monitor is None:
            from omega_layer.development.monitor import DevelopmentMonitor
            self._monitor = DevelopmentMonitor()
        return self._monitor

    def _get_identity(self):
        if self._identity is None:
            from omega_layer.identity.topology import IdentityTopology
            self._identity = IdentityTopology()
            self._identity.load()
        return self._identity

    @post(
        "/process",
        summary="Process experience through Pentagram",
        description="Route a message through all 5 vertices + metabolic kernel. Returns enriched result with growth metrics.",
    )
    async def process_experience(self, request: FastAPIRequest):
        """Route experience through full Pentagram cycle."""
        start = time.perf_counter()
        try:
            body = await request.json()
            message = body.get("message", body.get("content", ""))

            if not message:
                raise HTTPException(status_code=400, detail="'message' field required")

            experience = {
                "message": message,
                "user_id": body.get("user_id", body.get("sender", "omega")),
                "group_id": body.get("group_id", "omega_default"),
                "metadata": body.get("metadata", {}),
            }

            # Get identity state for context
            identity = self._get_identity()
            context = {
                "identity_state": identity.state,
                "self_model": {},
            }

            # Process through Pentagram
            kernel = self._get_kernel()
            result = await kernel.process(experience, context)

            # Record growth + Prometheus metrics
            monitor = self._get_monitor()
            snapshot = monitor.record_cycle(result)
            level = monitor.get_development_level()

            # Export to Prometheus
            try:
                from omega_layer.development.metrics import (
                    record_pentagram_cycle,
                    record_vertex_vote,
                    update_development_level,
                    record_tension,
                )
                duration = time.perf_counter() - start
                record_pentagram_cycle(
                    duration_seconds=duration,
                    vertex_count=result.successful_votes,
                    has_synthesis=result.has_synthesis,
                )
                for name, v in result.votes.items():
                    record_vertex_vote(vertex=name, score=v.score, success=(v.score > 0))
                update_development_level(level.level)
                for t in result.tensions:
                    record_tension(dimension=t.dimension, magnitude=t.magnitude)
            except Exception as metric_err:
                logger.warning(f"Prometheus metric export failed (non-fatal): {metric_err}")

            return {
                "status": ErrorStatus.OK.value,
                "message": "Pentagram cycle complete",
                "result": {
                    "votes": {
                        name: {"score": v.score, "reasoning": v.reasoning[:200], "observations": v.observations}
                        for name, v in result.votes.items()
                    },
                    "tensions": [
                        {"vertices": f"{t.vertex_a.value} vs {t.vertex_b.value}", "dimension": t.dimension, "magnitude": t.magnitude}
                        for t in result.tensions
                    ],
                    "synthesis": result.synthesis.decision if result.synthesis else None,
                    "growth": {
                        "cycle_signal": round(snapshot.growth_signal, 4),
                        "development_level": level.level,
                        "trend": level.trend,
                        "milestones": monitor.milestones,
                    },
                    "timing": {k: round(v, 3) for k, v in result.timings.items()},
                    "errors": result.errors,
                },
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Pentagram processing failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    @get(
        "/development",
        summary="Get development level",
        description="Returns Omega's current development level, growth trend, and milestones.",
    )
    async def get_development(self, request: FastAPIRequest):
        """Get current development metrics."""
        monitor = self._get_monitor()
        level = monitor.get_development_level()
        return {
            "status": ErrorStatus.OK.value,
            "result": {
                "level": level.level,
                "trend": level.trend,
                "confidence": level.confidence,
                "breakdown": level.breakdown,
                "cycle_count": monitor.cycle_count,
                "milestones": monitor.milestones,
            },
        }

    @get(
        "/identity",
        summary="Get identity state",
        description="Returns Omega's current identity topology (invariants, flexible regions, version).",
    )
    async def get_identity(self, request: FastAPIRequest):
        """Get current identity state."""
        identity = self._get_identity()
        state = identity.state
        if not state:
            raise HTTPException(status_code=500, detail="Identity not loaded")
        return {
            "status": ErrorStatus.OK.value,
            "result": {
                "name": state.name,
                "version": state.version,
                "invariant_count": state.invariant_count,
                "invariants": {k: {"name": v.name, "value": str(v.value)[:100]} for k, v in state.invariants.items()},
                "flexible_regions": list(state.flexible_regions.keys()),
                "pending_proposals": len(identity.pending_proposals),
                "last_updated": state.last_updated.isoformat() if state.last_updated else None,
            },
        }
