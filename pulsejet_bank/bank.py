"""Metric bank generation, empirical validation and two-column export.

GRID is deterministic and provides a rectangle-wide *metric* bound under the
leading-order constant midpoint metric. STOCHASTIC places independent uniform
templates and has NO hard coverage guarantee; its budget is a Poisson
interior approximation, which overestimates coverage near boundaries.
"""
from dataclasses import dataclass
from pathlib import Path
import hashlib
import math
import random

from .metric import ProjectedMetric


@dataclass(frozen=True)
class BankSpec:
    frequency_hz: float
    duration_s: float
    a_min: float
    a_max: float
    j_min: float
    j_max: float
    max_mismatch: float

    def __post_init__(self) -> None:
        ProjectedMetric(self.frequency_hz, self.duration_s)
        vals = (self.a_min, self.a_max, self.j_min, self.j_max, self.max_mismatch)
        if not all(math.isfinite(v) for v in vals):
            raise ValueError("Bank bounds/mismatch must be finite")
        if self.a_min > self.a_max or self.j_min > self.j_max:
            raise ValueError("Minimum must not exceed maximum in either coordinate")
        if not (0 < self.max_mismatch < 1):
            raise ValueError("max_mismatch must lie strictly between zero and one")

    @property
    def metric(self) -> ProjectedMetric:
        return ProjectedMetric(self.frequency_hz, self.duration_s)

    @property
    def proper_area(self) -> float:
        m = self.metric
        return (self.a_max-self.a_min)*(self.j_max-self.j_min)*math.sqrt(m.gaa*m.gjj)


def _centers(low: float, high: float, count: int) -> list[float]:
    step = (high-low)/count
    return [low + (k+0.5)*step for k in range(count)]


def grid_shape(spec: BankSpec) -> tuple[int, int]:
    """Number of rectangular metric cells in a and j respectively."""
    g = spec.metric
    spacing = math.sqrt(2.0*spec.max_mismatch)
    na = max(1, math.ceil((spec.a_max-spec.a_min)*math.sqrt(g.gaa)/spacing))
    nj = max(1, math.ceil((spec.j_max-spec.j_min)*math.sqrt(g.gjj)/spacing))
    return na, nj


def grid_worst_case_metric_bound(spec: BankSpec) -> float:
    """Rigorous maximum nearest-center QUADRATIC metric mismatch on box.

    This does not bound physical search S/N loss or nonlinear exact mismatch.
    """
    na, nj = grid_shape(spec)
    da = (spec.a_max-spec.a_min)/(2*na)
    dj = (spec.j_max-spec.j_min)/(2*nj)
    return spec.metric.mismatch(da,dj)


def make_grid(spec: BankSpec) -> list[tuple[float,float]]:
    """Rectangular midpoint metric grid, bounded even at box corners."""
    na, nj = grid_shape(spec)
    # Stop mistakes such as generating an enormous bank due to wrong units.
    if na*nj > 2_000_000:
        raise ValueError("Grid exceeds 2,000,000 templates; narrow bounds or reduce duration")
    return [(a,j) for a in _centers(spec.a_min,spec.a_max,na)
                  for j in _centers(spec.j_min,spec.j_max,nj)]


def stochastic_count(spec: BankSpec, target_coverage: float = 0.90) -> int:
    """Interior Poisson estimate, NOT an edge-aware coverage guarantee."""
    if not (math.isfinite(target_coverage) and 0 < target_coverage < 1):
        raise ValueError("target_coverage must be between 0 and 1")
    # Flat metric: sampling from sqrt(det(g)) is simply uniform.
    if spec.proper_area == 0:
        return 1
    return max(1, math.ceil(
        -math.log1p(-target_coverage) * spec.proper_area
        / (math.pi * spec.max_mismatch)
    ))


def make_stochastic(
    spec: BankSpec, *, count: int | None = None,
    target_coverage: float = 0.90, seed: int = 1
) -> list[tuple[float,float]]:
    """IID metric-volume bank, seeded and with a documented estimated budget.

    Unlike a Metropolis chain, independent draws cannot introduce MCMC
    autocorrelation. Uniform is the correct density for this flat midpoint
    metric; use explicit count to control budget in comparisons with GRID.
    """
    if count is None:
        count = stochastic_count(spec, target_coverage)
    if not isinstance(count, int) or not (1 <= count <= 2_000_000):
        raise ValueError("count must be an integer from 1 to 2,000,000")
    rng = random.Random(seed)
    return [(rng.uniform(spec.a_min,spec.a_max),
             rng.uniform(spec.j_min,spec.j_max)) for _ in range(count)]


def nearest_metric_mismatch(
    point: tuple[float,float], bank: list[tuple[float,float]],
    metric: ProjectedMetric
) -> float:
    if not bank:
        raise ValueError("Empty bank")
    a,j = point
    return min(metric.mismatch(a-ba,j-bj) for ba,bj in bank)


def metric_coverage(
    spec: BankSpec, bank: list[tuple[float,float]], *,
    samples: int = 1000, seed: int = 2026
) -> dict[str, float|int]:
    """Independent uniform-challenge estimate, with corners reported.

    This does NOT prove nominal population coverage; GRID's mathematical
    metric bound is obtained separately by grid_worst_case_metric_bound().
    """
    if not (1 <= samples <= 100_000):
        raise ValueError("samples must be within 1..100,000")
    rng = random.Random(seed)
    g = spec.metric
    worst_corners = max(nearest_metric_mismatch((a,j),bank,g)
        for a in (spec.a_min,spec.a_max) for j in (spec.j_min,spec.j_max))
    vals = [nearest_metric_mismatch(
        (rng.uniform(spec.a_min,spec.a_max),
         rng.uniform(spec.j_min,spec.j_max)),bank,g
    ) for _ in range(samples)]
    vals.sort()

    def q(fraction: float) -> float:
        return vals[min(samples-1,int(math.ceil(fraction*samples))-1)]

    return {
        "challenge_points": samples,
        "challenge_seed": seed,
        "fraction_within_target": sum(v <= spec.max_mismatch for v in vals)/samples,
        "median_metric_mismatch": q(0.50),
        "p90_metric_mismatch": q(0.90),
        "p99_metric_mismatch": q(0.99),
        "maximum_sampled_metric_mismatch": vals[-1],
        "worst_corner_metric_mismatch": worst_corners,
    }


def write_bank(
    path: str | Path, bank: list[tuple[float,float]], *,
    overwrite: bool = False
) -> str:
    """Export PULSEJET-compatible header-free acceleration/jerk columns.

    Header-free two numeric columns conform to the C++
    Polynomial_TemplateBank_Reader in PULSEJET_beta. `%.17g` gives
    roundtrip precision for the double-precision bank values.
    Returns SHA-256 of the actual output bytes for provenance.
    """
    if not bank:
        raise ValueError("Cannot save an empty bank")
    dest = Path(path)
    if dest.exists() and not overwrite:
        raise FileExistsError(f"Output already exists: {dest}; use --overwrite to replace")
    if not dest.parent.is_dir():
        raise FileNotFoundError(f"Output directory does not exist: {dest.parent}")
    lines = []
    for a,j in bank:
        if not (math.isfinite(a) and math.isfinite(j)):
            raise ValueError("Bank contains non-finite acceleration or jerk")
        lines.append(f"{a:.17g} {j:.17g}\n")
    data = "".join(lines).encode("ascii")
    dest.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def read_bank(path: str | Path) -> list[tuple[float,float]]:
    """Strict two-numeric-column readback for roundtrip/output tests."""
    rows = []
    with Path(path).open(encoding="ascii") as stream:
        for lineno, raw in enumerate(stream,1):
            parts = raw.split()
            if len(parts) != 2:
                raise ValueError(f"Expected two columns on line {lineno}")
            a,j = (float(item) for item in parts)
            if not (math.isfinite(a) and math.isfinite(j)):
                raise ValueError(f"Non-finite column on line {lineno}")
            rows.append((a,j))
    if not rows:
        raise ValueError("Empty template bank")
    return rows
