"""
CrossReferenceMiner - Find connections across Omega's accumulated memories.

Uses existing EverMemOS agentic retrieval (multi-round LLM-guided search)
to discover patterns distributed across the memory corpus.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class CrossReferenceInsight:
    """A connection discovered across multiple existing memories."""

    synthesis: str
    source_references: List[str]
    confidence: float = 0.5
    domains_bridged: List[str] = None

    def __post_init__(self):
        if self.domains_bridged is None:
            self.domains_bridged = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "synthesis": self.synthesis,
            "source_references": self.source_references,
            "confidence": self.confidence,
            "domains_bridged": self.domains_bridged,
        }


class CrossReferenceMiner:
    """Mines connections across Omega's accumulated memory corpus.

    Uses the existing MemoryManager's agentic retrieval (multi-round
    LLM-guided search with sufficiency checking) to find related
    memories, then synthesizes cross-document patterns.

    Usage:
        miner = CrossReferenceMiner(memory_manager=mm, llm_provider=llm)
        insights = await miner.mine("architecture patterns")
    """

    def __init__(self, memory_manager=None, llm_provider=None):
        self._memory_manager = memory_manager
        self._llm_provider = llm_provider

    async def mine(
        self,
        seed_concept: str,
        user_id: str = "omega",
        group_id: str = "omega_default",
        top_k: int = 15,
    ) -> List[CrossReferenceInsight]:
        """Mine for cross-references related to a seed concept.

        Args:
            seed_concept: The concept or question to explore
            user_id: User scope for retrieval
            group_id: Group scope for retrieval
            top_k: Max memories to retrieve

        Returns:
            List of CrossReferenceInsight objects
        """
        if not self._memory_manager or not self._llm_provider:
            logger.warning("CrossReferenceMiner: memory_manager or llm not configured")
            return []

        try:
            from api_specs.dtos import RetrieveMemRequest
            from api_specs.memory_models import MemoryType, RetrieveMethod

            # Use agentic retrieval for deep multi-round search
            request = RetrieveMemRequest(
                query=seed_concept,
                user_id=user_id,
                group_id=group_id,
                top_k=top_k,
                memory_types=[MemoryType.EPISODIC_MEMORY],
                retrieve_method=RetrieveMethod.AGENTIC,
            )

            response = await self._memory_manager.retrieve_mem(request)

            if not response or not response.memories:
                return []

            # Synthesize cross-references via LLM
            memory_summaries = []
            for mem_group in response.memories[:5]:
                if isinstance(mem_group, dict):
                    for gid, mems in mem_group.items():
                        for m in (mems if isinstance(mems, list) else [mems]):
                            text = getattr(m, 'episode', None) or getattr(m, 'summary', str(m))
                            memory_summaries.append(str(text)[:300])

            if not memory_summaries:
                return []

            prompt = f"""You are Omega, analyzing connections across your accumulated memories.

Seed concept: {seed_concept}

Related memories found:
{chr(10).join(f'- {s}' for s in memory_summaries)}

What cross-references or connections do you see between these memories?
What synthesized understanding forms from combining them?

Return JSON array:
[{{"synthesis": "...", "source_count": N, "domains_bridged": ["domain1", "domain2"], "confidence": 0.0-1.0}}]

Return empty array [] if no meaningful connections found."""

            response_text = await self._llm_provider.generate(
                prompt, temperature=0.3, max_tokens=1500
            )

            import json
            text = response_text.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            data = json.loads(text)

            if not isinstance(data, list):
                return []

            insights = []
            for item in data:
                if isinstance(item, dict) and "synthesis" in item:
                    insights.append(CrossReferenceInsight(
                        synthesis=item["synthesis"],
                        source_references=memory_summaries[:3],
                        confidence=min(1.0, max(0.0, item.get("confidence", 0.5))),
                        domains_bridged=item.get("domains_bridged", []),
                    ))

            logger.info(f"CrossReferenceMiner: {len(insights)} insights from '{seed_concept[:50]}'")
            return insights

        except Exception as e:
            logger.error(f"CrossReferenceMiner failed: {e}", exc_info=True)
            return []
