"""
BaseVertex - Abstract base class for all Pentagram cognitive faculties.

Each vertex processes every experience from its unique perspective
and produces a VertexVote. Vertices run in parallel (except Orchestra,
which runs after the others to synthesize communication).

Vertex constraints (from omega_scar.json):
  Ledger gives:   persistence, lineage, auditability, what_happened
  Garden gives:   consolidation, pruning, abstraction, what_it_means
  Mirror gives:   self_model, perspective, reflexivity, who_is_seeing
  Compass gives:  priority, ethics, teleology, why_act
  Orchestra gives: alignment, shared_reality, synchronization, with_what
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from omega_layer.kernel.schemas import VertexName, VertexVote

logger = logging.getLogger(__name__)


class BaseVertex(ABC):
    """Abstract base class for Pentagram vertices.

    All vertices implement vote() which takes an experience and returns
    a VertexVote containing their perspective on it.

    Subclasses should:
    1. Set self.vertex_name in __init__
    2. Implement vote() with their specific analysis logic
    3. Use _call_llm() for LLM interactions
    4. Use _build_vote() helper to construct standardized votes
    """

    def __init__(self, vertex_name: VertexName):
        self.vertex_name = vertex_name
        self._llm_provider = None  # Set via configure_llm()

    def configure_llm(self, llm_provider) -> None:
        """Configure the LLM provider for this vertex.

        Args:
            llm_provider: An LLMProvider instance from memory_layer/llm/
        """
        self._llm_provider = llm_provider

    @abstractmethod
    async def vote(
        self,
        experience: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> VertexVote:
        """Process an experience and return this vertex's assessment.

        Args:
            experience: The experience dict containing at minimum:
                - message: str (the conversation/content)
                - metadata: dict (timestamps, participants, etc.)
            context: Optional additional context (e.g., other vertex votes
                for Orchestra, identity state for Mirror)

        Returns:
            VertexVote with this vertex's perspective on the experience.
        """
        ...

    async def _call_llm(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> str:
        """Call the LLM with a prompt and return the response text.

        Args:
            prompt: The formatted prompt string
            temperature: LLM temperature (lower = more deterministic)
            max_tokens: Maximum response tokens

        Returns:
            Raw response text from LLM

        Raises:
            RuntimeError: If LLM provider not configured
        """
        if self._llm_provider is None:
            raise RuntimeError(
                f"{self.vertex_name.value} vertex: LLM provider not configured. "
                f"Call configure_llm() before vote()."
            )

        start = time.perf_counter()
        try:
            response = await self._llm_provider.generate(
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            duration = time.perf_counter() - start
            logger.debug(
                f"[{self.vertex_name.value}] LLM call completed in {duration:.2f}s "
                f"({len(response)} chars)"
            )
            return response
        except Exception as e:
            duration = time.perf_counter() - start
            logger.error(
                f"[{self.vertex_name.value}] LLM call failed after {duration:.2f}s: {e}"
            )
            raise

    def _build_vote(
        self,
        score: float,
        reasoning: str,
        action_proposals: Optional[List[Dict[str, Any]]] = None,
        observations: Optional[List[str]] = None,
        attachments: Optional[Dict[str, Any]] = None,
    ) -> VertexVote:
        """Helper to construct a standardized VertexVote.

        Args:
            score: 0.0-1.0 relevance/importance from this vertex's perspective
            reasoning: Explanation of the assessment
            action_proposals: Proposed actions
            observations: Notable observations
            attachments: Additional data (retrieved memories, patterns, etc.)

        Returns:
            A validated VertexVote instance
        """
        return VertexVote(
            vertex_name=self.vertex_name,
            score=max(0.0, min(1.0, score)),  # Clamp to [0, 1]
            reasoning=reasoning,
            action_proposals=action_proposals or [],
            observations=observations or [],
            attachments=attachments or {},
        )

    def _build_error_vote(self, error: Exception) -> VertexVote:
        """Build a minimal vote when processing fails.

        Rather than crashing the entire Pentagram cycle when one vertex
        fails, return a low-confidence error vote so the kernel can
        still synthesize from the remaining vertices.

        Args:
            error: The exception that occurred

        Returns:
            A minimal VertexVote with score=0 and error details
        """
        logger.warning(
            f"[{self.vertex_name.value}] Building error vote: {error}"
        )
        return VertexVote(
            vertex_name=self.vertex_name,
            score=0.0,
            reasoning=f"Error during {self.vertex_name.value} processing: {str(error)}",
            action_proposals=[],
            observations=[f"vertex_error: {type(error).__name__}: {str(error)}"],
            attachments={"error": True, "error_type": type(error).__name__},
        )

    def _parse_json_response(self, response: str) -> Any:
        """Parse JSON from LLM response, handling markdown code blocks.

        Args:
            response: Raw LLM response text

        Returns:
            Parsed JSON (dict or list)

        Raises:
            ValueError: If JSON parsing fails
        """
        import json

        text = response.strip()

        # Handle ```json ... ``` blocks
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            if end > start:
                text = text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            if end > start:
                text = text[start:end].strip()

        # Try parsing directly
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try finding JSON object or array in the text
        import re

        # Try object
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        # Try array
        match = re.search(r'\[[\s\S]*\]', text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        raise ValueError(
            f"Failed to parse JSON from {self.vertex_name.value} LLM response: "
            f"{text[:200]}..."
        )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(vertex={self.vertex_name.value})"
