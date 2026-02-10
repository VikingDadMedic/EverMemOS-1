"""
InsightExtractor - Extracts what Omega LEARNED from any conversation.

Domain-agnostic. A conversation about cooking can teach Omega about
patience. A code review can teach about communication styles.
Extends the existing MemoryExtractor pattern.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from memory_layer.memory_extractor.base_memory_extractor import (
    MemoryExtractor,
    MemoryExtractRequest,
)
from api_specs.memory_types import MemoryType, BaseMemory
from omega_layer.prompts.en.insight_prompts import INSIGHT_EXTRACTION_PROMPT

logger = logging.getLogger(__name__)


@dataclass
class Insight:
    """A single insight Omega extracted from experience."""

    insight: str
    evidence: str
    domain: str
    depth_level: int = 1  # 1-5
    novelty_score: float = 0.0  # 0-1
    connects_to: str = "none"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "insight": self.insight,
            "evidence": self.evidence,
            "domain": self.domain,
            "depth_level": self.depth_level,
            "novelty_score": self.novelty_score,
            "connects_to": self.connects_to,
        }


class InsightExtractor(MemoryExtractor):
    """Extracts what Omega learned from any conversation.

    Uses LLM to analyze conversation for new understanding,
    novel connections, key takeaways. Domain-agnostic.
    """

    def __init__(self, llm_provider=None):
        super().__init__(MemoryType.EPISODIC_MEMORY)  # Closest existing type
        self.llm_provider = llm_provider

    async def extract_memory(
        self, request: MemoryExtractRequest
    ) -> Optional[List[Insight]]:
        """Extract insights from a MemCell.

        Args:
            request: MemoryExtractRequest with memcell

        Returns:
            List of Insight objects, or None if extraction fails
        """
        if not request.memcell or not self.llm_provider:
            return None

        try:
            # Build conversation text from memcell original data
            conversation = self._format_conversation(request.memcell.original_data)
            existing_context = "No existing context available"  # TODO: retrieve from memory

            prompt = INSIGHT_EXTRACTION_PROMPT.format(
                conversation=conversation,
                existing_context=existing_context,
            )

            response = await self.llm_provider.generate(
                prompt, temperature=0.3, max_tokens=2000
            )

            insights_data = self._parse_json(response)
            if not isinstance(insights_data, list):
                return []

            insights = []
            for item in insights_data:
                if isinstance(item, dict) and "insight" in item:
                    insights.append(Insight(
                        insight=item["insight"],
                        evidence=item.get("evidence", ""),
                        domain=item.get("domain", "general"),
                        depth_level=min(5, max(1, item.get("depth_level", 1))),
                        novelty_score=min(1.0, max(0.0, item.get("novelty_score", 0.0))),
                        connects_to=item.get("connects_to", "none"),
                    ))

            logger.info(f"InsightExtractor: Extracted {len(insights)} insights")
            return insights if insights else None

        except Exception as e:
            logger.error(f"InsightExtractor failed: {e}", exc_info=True)
            return None

    def _format_conversation(self, data_list: List[Dict]) -> str:
        lines = []
        for data in data_list:
            speaker = data.get("speaker_name") or data.get("sender", "Unknown")
            content = data.get("content", "")
            timestamp = data.get("timestamp", "")
            if timestamp:
                lines.append(f"[{timestamp}] {speaker}: {content}")
            else:
                lines.append(f"{speaker}: {content}")
        return "\n".join(lines)

    def _parse_json(self, response: str) -> Any:
        text = response.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        return json.loads(text)
