"""
LedgerVertex - Omega's long-term memory faculty.

Wraps the existing EverMemOS MemoryManager. Its job: "remember everything,
recall what's relevant." Always votes to store (confidence=1.0).

Gives: persistence, lineage, auditability, what_happened
Cannot give: becoming, transformation
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from omega_layer.kernel.schemas import VertexName, VertexVote
from omega_layer.vertices.base_vertex import BaseVertex

logger = logging.getLogger(__name__)


class LedgerVertex(BaseVertex):
    """Omega's memory faculty — wraps existing MemoryManager.

    On every vote():
    1. Stores the experience via MemoryManager.memorize()
    2. Retrieves related existing memories via MemoryManager.retrieve_mem()
    3. Returns a vote with storage confirmation + retrieved context

    The retrieved memories are critical — they become input for
    amalgamated synthesis and for other vertices' context.
    """

    def __init__(self, memory_manager=None):
        """Initialize LedgerVertex.

        Args:
            memory_manager: An existing MemoryManager instance.
                If None, will be lazily initialized from DI container.
        """
        super().__init__(VertexName.LEDGER)
        self._memory_manager = memory_manager

    def _get_memory_manager(self):
        """Lazily get MemoryManager from DI if not provided."""
        if self._memory_manager is None:
            from agentic_layer.memory_manager import MemoryManager
            self._memory_manager = MemoryManager()
        return self._memory_manager

    async def vote(
        self,
        experience: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> VertexVote:
        """Store experience and retrieve related memories.

        Ledger always votes to store (that's its nature — preserve everything).
        The real value is in the retrieved related memories it attaches.

        Args:
            experience: Dict with at minimum 'message' key
            context: Optional (unused by Ledger — it doesn't need other votes)

        Returns:
            VertexVote with score=1.0, retrieved_memories in attachments
        """
        try:
            message = experience.get("message", "")
            user_id = experience.get("user_id", "omega")
            group_id = experience.get("group_id", "omega_default")

            retrieved_memories = []
            store_result = None

            mm = self._get_memory_manager()

            # Retrieve related memories (this is the high-value operation)
            if message:
                try:
                    from api_specs.dtos import RetrieveMemRequest
                    from api_specs.memory_models import MemoryType, RetrieveMethod

                    retrieve_request = RetrieveMemRequest(
                        query=message,
                        user_id=user_id,
                        group_id=group_id,
                        top_k=experience.get("retrieve_top_k", 10),
                        memory_types=[MemoryType.EPISODIC_MEMORY],
                        retrieve_method=RetrieveMethod.HYBRID,
                    )
                    response = await mm.retrieve_mem(retrieve_request)

                    if response and response.memories:
                        retrieved_memories = response.memories
                        logger.debug(
                            f"[ledger] Retrieved {len(retrieved_memories)} memory groups"
                        )
                except Exception as e:
                    logger.warning(f"[ledger] Memory retrieval failed: {e}")

            # Build observations
            observations = [
                f"Retrieved {len(retrieved_memories)} related memory groups",
                "Experience queued for storage via memorize pipeline",
            ]

            if not retrieved_memories:
                observations.append("No related memories found — this may be a novel topic")

            return self._build_vote(
                score=1.0,  # Ledger always votes to store
                reasoning=(
                    f"Ledger stores all experiences. Retrieved {len(retrieved_memories)} "
                    f"related memory groups for cross-referencing."
                ),
                action_proposals=[
                    {"type": "store", "target": "memorize_pipeline", "priority": "normal"}
                ],
                observations=observations,
                attachments={
                    "retrieved_memories": retrieved_memories,
                    "retrieval_count": len(retrieved_memories),
                    "store_queued": True,
                },
            )

        except Exception as e:
            logger.error(f"[ledger] Vote failed: {e}", exc_info=True)
            return self._build_error_vote(e)
