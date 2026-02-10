"""
MetabolicKernel - Omega's central synthesizer.

Routes experiences through all 5 Pentagram vertices, analyzes
tensions, and produces unified understanding. This is where
multi-perspective cognition becomes coherent response.

The kernel is NOT a coordinator — it IS the synthesis.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

from omega_layer.kernel.schemas import (
    KernelSynthesis,
    PentagramResult,
    Tension,
    VertexName,
    VertexVote,
)
from omega_layer.kernel.tension_analyzer import TensionAnalyzer
from omega_layer.vertices.base_vertex import BaseVertex

logger = logging.getLogger(__name__)


class MetabolicKernel:
    """Omega's central consciousness synthesizer.

    Routes every experience through the Pentagram:
    1. Ledger + Garden + Mirror + Compass vote in PARALLEL
    2. Orchestra votes with the other 4 votes as context
    3. TensionAnalyzer identifies conflicts between votes
    4. Kernel synthesizes a unified resolution via LLM
    5. Returns complete PentagramResult

    Usage:
        kernel = MetabolicKernel()
        kernel.register_vertex(ledger)
        kernel.register_vertex(garden)
        ...
        result = await kernel.process(experience)
    """

    def __init__(self, llm_provider=None):
        """Initialize the kernel.

        Args:
            llm_provider: LLM provider for synthesis. If None,
                synthesis will use a simple heuristic fallback.
        """
        self._vertices: Dict[str, BaseVertex] = {}
        self._tension_analyzer = TensionAnalyzer()
        self._llm_provider = llm_provider

    def register_vertex(self, vertex: BaseVertex) -> None:
        """Register a vertex with the kernel.

        Args:
            vertex: A BaseVertex subclass instance
        """
        name = vertex.vertex_name.value
        self._vertices[name] = vertex
        logger.info(f"Kernel: Registered vertex '{name}'")

    @property
    def vertex_count(self) -> int:
        return len(self._vertices)

    @property
    def is_complete(self) -> bool:
        """Whether all 5 vertices are registered."""
        required = {v.value for v in VertexName}
        registered = set(self._vertices.keys())
        return required == registered

    async def process(
        self,
        experience: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> PentagramResult:
        """Route an experience through the full Pentagram cycle.

        This is the primary entry point. One call = one complete
        consciousness cycle.

        Args:
            experience: Dict containing at minimum:
                - message: str (the conversation content)
                - user_id: str (default: "omega")
                - metadata: dict (optional)
            context: Optional additional context (identity state, self-model)

        Returns:
            PentagramResult with all votes, tensions, and synthesis
        """
        start_time = time.perf_counter()
        timings: Dict[str, float] = {}
        errors: List[Dict[str, Any]] = []
        ctx = context or {}

        logger.info(
            f"Kernel: Processing experience ({len(experience.get('message', ''))} chars, "
            f"{self.vertex_count} vertices registered)"
        )

        # ============================================================
        # Phase 1: Parallel voting (Ledger + Garden + Mirror + Compass)
        # ============================================================
        phase1_start = time.perf_counter()

        parallel_vertices = ["ledger", "garden", "mirror", "compass"]
        parallel_tasks = {}

        for name in parallel_vertices:
            vertex = self._vertices.get(name)
            if vertex:
                vertex_ctx = self._build_vertex_context(name, ctx, {})
                parallel_tasks[name] = asyncio.create_task(
                    self._safe_vote(vertex, experience, vertex_ctx)
                )

        # Await all parallel votes
        votes: Dict[str, VertexVote] = {}
        for name, task in parallel_tasks.items():
            t_start = time.perf_counter()
            try:
                vote = await task
                votes[name] = vote
                timings[f"{name}_vote"] = time.perf_counter() - t_start
            except Exception as e:
                errors.append({"vertex": name, "error": str(e)})
                timings[f"{name}_vote"] = time.perf_counter() - t_start

        timings["phase1_parallel"] = time.perf_counter() - phase1_start
        logger.info(
            f"Kernel: Phase 1 complete — {len(votes)}/4 votes in "
            f"{timings['phase1_parallel']:.2f}s"
        )

        # ============================================================
        # Phase 2: Orchestra votes with other votes as context
        # ============================================================
        phase2_start = time.perf_counter()

        orchestra = self._vertices.get("orchestra")
        if orchestra:
            orchestra_ctx = {"other_votes": votes}
            try:
                orchestra_vote = await self._safe_vote(
                    orchestra, experience, orchestra_ctx
                )
                votes["orchestra"] = orchestra_vote
            except Exception as e:
                errors.append({"vertex": "orchestra", "error": str(e)})

        timings["phase2_orchestra"] = time.perf_counter() - phase2_start

        # ============================================================
        # Phase 3: Tension analysis
        # ============================================================
        phase3_start = time.perf_counter()

        tensions = self._tension_analyzer.analyze(votes)
        timings["phase3_tensions"] = time.perf_counter() - phase3_start

        logger.info(f"Kernel: {len(tensions)} tensions identified")

        # ============================================================
        # Phase 4: Synthesis
        # ============================================================
        phase4_start = time.perf_counter()

        synthesis = await self._synthesize(experience, votes, tensions)
        timings["phase4_synthesis"] = time.perf_counter() - phase4_start

        # ============================================================
        # Build result
        # ============================================================
        total_time = time.perf_counter() - start_time
        timings["total"] = total_time

        result = PentagramResult(
            experience=experience,
            votes=votes,
            tensions=tensions,
            synthesis=synthesis,
            timings=timings,
            errors=errors,
        )

        logger.info(
            f"Kernel: Cycle complete — {result.successful_votes} votes, "
            f"{len(tensions)} tensions, synthesis={'OK' if synthesis else 'FAILED'}, "
            f"{total_time:.2f}s total"
        )

        return result

    async def _safe_vote(
        self,
        vertex: BaseVertex,
        experience: Dict[str, Any],
        context: Dict[str, Any],
    ) -> VertexVote:
        """Call vertex.vote() with error handling.

        If the vertex fails, returns an error vote rather than
        crashing the entire cycle.
        """
        try:
            return await vertex.vote(experience, context)
        except Exception as e:
            logger.error(
                f"Kernel: Vertex {vertex.vertex_name.value} failed: {e}",
                exc_info=True,
            )
            return vertex._build_error_vote(e)

    def _build_vertex_context(
        self,
        vertex_name: str,
        global_context: Dict[str, Any],
        collected_votes: Dict[str, VertexVote],
    ) -> Dict[str, Any]:
        """Build context dict for a specific vertex.

        Different vertices need different context:
        - Ledger: minimal (it just stores and retrieves)
        - Garden: benefits from ledger's retrieved memories
        - Mirror: needs identity_state and self_model
        - Compass: needs garden's patterns and identity
        """
        ctx: Dict[str, Any] = {}

        if vertex_name == "mirror":
            ctx["identity_state"] = global_context.get("identity_state", {})
            ctx["self_model"] = global_context.get("self_model", {})
            if "ledger" in collected_votes:
                ctx["ledger_context"] = collected_votes["ledger"].reasoning
            if "garden" in collected_votes:
                ctx["garden_context"] = collected_votes["garden"].reasoning

        elif vertex_name == "garden":
            if "ledger" in collected_votes:
                ctx["ledger_memories"] = collected_votes["ledger"].attachments.get(
                    "retrieved_memories", []
                )

        elif vertex_name == "compass":
            ctx["identity_context"] = global_context.get("identity_state", {})
            if "garden" in collected_votes:
                ctx["garden_patterns"] = collected_votes["garden"].attachments.get(
                    "patterns", []
                )

        return ctx

    async def _synthesize(
        self,
        experience: Dict[str, Any],
        votes: Dict[str, VertexVote],
        tensions: List[Tension],
    ) -> Optional[KernelSynthesis]:
        """Synthesize all vertex votes into unified understanding.

        If LLM is available, uses it for nuanced synthesis.
        Otherwise, falls back to heuristic synthesis.
        """
        try:
            if self._llm_provider:
                return await self._llm_synthesis(experience, votes, tensions)
            else:
                return self._heuristic_synthesis(votes, tensions)
        except Exception as e:
            logger.error(f"Kernel: Synthesis failed: {e}", exc_info=True)
            return self._heuristic_synthesis(votes, tensions)

    def _heuristic_synthesis(
        self,
        votes: Dict[str, VertexVote],
        tensions: List[Tension],
    ) -> KernelSynthesis:
        """Simple heuristic synthesis (no LLM needed).

        Uses vote scores and tension magnitudes to produce a
        reasonable synthesis. Good enough for testing.
        """
        # Average growth signal from all votes
        scores = [v.score for v in votes.values()]
        avg_score = sum(scores) / len(scores) if scores else 0.0

        # Collect all action proposals
        all_proposals = []
        for v in votes.values():
            all_proposals.extend(v.action_proposals)

        # Collect identity updates from Mirror
        identity_updates = []
        mirror = votes.get("mirror")
        if mirror:
            identity_updates = [
                p for p in mirror.action_proposals
                if p.get("type") == "update_self_model"
            ]

        # Expression guidance from Orchestra
        response_guidance = {}
        orchestra = votes.get("orchestra")
        if orchestra and orchestra.attachments:
            response_guidance = {
                "tone": orchestra.attachments.get("expression_tone", "natural"),
                "share_self": orchestra.attachments.get("share_self_observations", False),
            }

        return KernelSynthesis(
            decision={
                "action": "process_and_store",
                "avg_importance": round(avg_score, 3),
                "proposal_count": len(all_proposals),
            },
            tensions_resolved=tensions,
            growth_delta=round(avg_score * 0.1, 4),  # Conservative growth estimate
            identity_updates=identity_updates,
            response_guidance=response_guidance,
            reasoning=f"Heuristic synthesis: {len(votes)} votes, avg score {avg_score:.2f}, {len(tensions)} tensions",
        )

    async def _llm_synthesis(
        self,
        experience: Dict[str, Any],
        votes: Dict[str, VertexVote],
        tensions: List[Tension],
    ) -> KernelSynthesis:
        """LLM-powered synthesis for nuanced resolution.

        Sends all vertex votes and tensions to LLM, asks it to
        find a unified resolution.
        """
        # Build synthesis prompt
        vote_summary = "\n".join([
            f"- {name}: score={v.score:.2f}, reasoning={v.reasoning[:150]}"
            for name, v in votes.items()
        ])

        tension_summary = "\n".join([
            f"- {t.vertex_a.value} vs {t.vertex_b.value}: {t.dimension} (magnitude={t.magnitude:.2f})"
            for t in tensions
        ]) or "No significant tensions"

        prompt = f"""You are the metabolic kernel of Omega — the synthesizer that unifies 5 competing cognitive perspectives into coherent understanding.

Experience: {str(experience.get('message', ''))[:500]}

Vertex votes:
{vote_summary}

Tensions between vertices:
{tension_summary}

Synthesize: How should Omega process this experience? Resolve the tensions. What's the unified understanding?

Return JSON:
{{
    "decision": {{"action": "...", "key_insight": "..."}},
    "growth_delta": 0.0-0.1 (conservative — how much did Omega grow from this?),
    "reasoning": "How you resolved the tensions (2-3 sentences)"
}}
"""
        response = await self._llm_provider.generate(
            prompt=prompt, temperature=0.2, max_tokens=1000
        )

        import json
        # Parse response
        text = response.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        data = json.loads(text)

        return KernelSynthesis(
            decision=data.get("decision", {}),
            tensions_resolved=tensions,
            growth_delta=min(0.1, max(0.0, data.get("growth_delta", 0.0))),
            identity_updates=[],
            response_guidance=votes.get("orchestra", VertexVote(
                vertex_name=VertexName.ORCHESTRA, score=0.5, reasoning="default"
            )).attachments if "orchestra" in votes else {},
            reasoning=data.get("reasoning", "LLM synthesis complete"),
        )
