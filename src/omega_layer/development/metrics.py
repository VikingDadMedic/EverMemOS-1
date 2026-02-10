"""
Omega Development Metrics

Prometheus metrics for monitoring Omega's growth and Pentagram performance.

Usage:
    from omega_layer.development.metrics import (
        record_pentagram_cycle,
        record_vertex_vote,
        update_development_level,
    )

    record_pentagram_cycle(duration_seconds=1.5, vertex_count=5, has_synthesis=True)
    record_vertex_vote(vertex='garden', score=0.75)
    update_development_level(level=0.087, trend='growing')
"""

from core.observation.metrics import Counter, Histogram, HistogramBuckets

# ============================================================
# Pentagram Cycle Metrics
# ============================================================

omega_pentagram_cycles_total = Counter(
    'omega_pentagram_cycles_total',
    'Total Pentagram cycles processed',
    ['status'],  # success, partial, error
)

omega_pentagram_cycle_duration_seconds = Histogram(
    'omega_pentagram_cycle_duration_seconds',
    'Duration of complete Pentagram cycle in seconds',
    ['status'],
    buckets=[0.5, 1.0, 2.0, 3.0, 5.0, 10.0, 30.0],
)

# ============================================================
# Vertex Metrics
# ============================================================

omega_vertex_votes_total = Counter(
    'omega_vertex_votes_total',
    'Total vertex votes produced',
    ['vertex', 'status'],  # vertex: ledger/garden/mirror/compass/orchestra, status: success/error
)

omega_vertex_score = Histogram(
    'omega_vertex_score',
    'Distribution of vertex vote scores',
    ['vertex'],
    buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
)

# ============================================================
# Development / Growth Metrics
# ============================================================

omega_development_level = Histogram(
    'omega_development_level',
    'Current Omega development level (0-1)',
    [],
    buckets=[0.05, 0.10, 0.15, 0.20, 0.30, 0.40, 0.50, 0.60, 0.80, 1.0],
)

omega_self_reference_depth = Histogram(
    'omega_self_reference_depth',
    'Self-reference depth from Mirror vertex (0-5)',
    [],
    buckets=[0, 1, 2, 3, 4, 5],
)

omega_amalgamation_total = Counter(
    'omega_amalgamation_total',
    'Total amalgamated memories created',
    ['synthesis_type'],  # extension, correction, connection, novel
)

omega_milestones_total = Counter(
    'omega_milestones_total',
    'Total development milestones achieved',
    ['milestone_type'],  # first_meta_cognitive, first_cross_domain, deep_self_reference
)

omega_identity_version = Counter(
    'omega_identity_version_changes_total',
    'Total identity version changes',
    [],
)

# ============================================================
# Tension Metrics
# ============================================================

omega_tensions_total = Counter(
    'omega_tensions_total',
    'Total tensions detected between vertices',
    ['dimension'],  # storage_vs_pruning, self_relevance_vs_strategic_value, etc.
)

omega_tension_magnitude = Histogram(
    'omega_tension_magnitude',
    'Distribution of tension magnitudes',
    [],
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
)


# ============================================================
# Helper Functions
# ============================================================


def record_pentagram_cycle(
    duration_seconds: float,
    vertex_count: int,
    has_synthesis: bool,
) -> None:
    """Record a completed Pentagram cycle."""
    status = 'success' if has_synthesis and vertex_count >= 4 else (
        'partial' if vertex_count > 0 else 'error'
    )
    omega_pentagram_cycles_total.labels(status=status).inc()
    omega_pentagram_cycle_duration_seconds.labels(status=status).observe(duration_seconds)


def record_vertex_vote(vertex: str, score: float, success: bool = True) -> None:
    """Record a vertex vote."""
    status = 'success' if success else 'error'
    omega_vertex_votes_total.labels(vertex=vertex, status=status).inc()
    if success:
        omega_vertex_score.labels(vertex=vertex).observe(score)


def update_development_level(level: float) -> None:
    """Record current development level."""
    omega_development_level.observe(level)


def record_amalgamation(synthesis_type: str) -> None:
    """Record an amalgamated memory creation."""
    omega_amalgamation_total.labels(synthesis_type=synthesis_type).inc()


def record_milestone(milestone_type: str) -> None:
    """Record a development milestone."""
    omega_milestones_total.labels(milestone_type=milestone_type).inc()


def record_tension(dimension: str, magnitude: float) -> None:
    """Record a detected tension."""
    omega_tensions_total.labels(dimension=dimension).inc()
    omega_tension_magnitude.observe(magnitude)
