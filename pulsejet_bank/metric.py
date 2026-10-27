"""Analytical small-mismatch, frequency-projected polynomial phase metric.

For midpoint tau in [-T/2, T/2], the leading-order phase derivatives are

  d(phi)/da = -pi*f*tau^2/c
  d(phi)/dj = -pi*f*tau^3/(3*c)
  d(phi)/df = 2*pi*tau   (at leading order in acceleration and jerk)

Remove arbitrary phase by centering derivatives; project out spin frequency
through the Schur complement of their covariance matrix.

  g_aa = pi^2*f^2*T^4/(180*c^2)
  g_aj = 0
  g_jj = pi^2*f^2*T^6/(25200*c^2)

The metric predicts LOSS OF COHERENT POWER (not loss of amplitude):
  mu ~ g_aa*(Delta a)^2 + g_jj*(Delta j)^2 .

This is local, first-order in velocity/c and small phase mismatch. The
harmonic-summed PULSEJET candidate S/N has no guaranteed identical loss.
"""
from dataclasses import dataclass
import math

from .phase import C_M_PER_S


@dataclass(frozen=True)
class ProjectedMetric:
    frequency_hz: float
    duration_s: float

    def __post_init__(self) -> None:
        if not math.isfinite(self.frequency_hz) or self.frequency_hz <= 0:
            raise ValueError("frequency_hz must be finite and > 0")
        if not math.isfinite(self.duration_s) or self.duration_s <= 0:
            raise ValueError("duration_s must be finite and > 0")

    @property
    def gaa(self) -> float:
        return (math.pi * self.frequency_hz / C_M_PER_S)**2 * self.duration_s**4 / 180.0

    @property
    def gaj(self) -> float:
        # The phase derivatives have opposite parity at the midpoint.
        return 0.0

    @property
    def gjj(self) -> float:
        return (math.pi * self.frequency_hz / C_M_PER_S)**2 * self.duration_s**6 / 25200.0

    def mismatch(self, delta_a: float, delta_j: float) -> float:
        return self.gaa * delta_a**2 + self.gjj * delta_j**2

    def whitening(self, acceleration: float, jerk: float) -> tuple[float, float]:
        """Map physical (a,j) into Euclidean coordinates of metric space."""
        return (math.sqrt(self.gaa) * acceleration,
                math.sqrt(self.gjj) * jerk)


def projected_metric_numerical(
    frequency_hz: float, duration_s: float, samples: int = 8192
) -> tuple[float, float, float]:
    """Independent midpoint numerical covariance & Schur calculation.

    Does not call ProjectedMetric; midpoint-rule quadrature verifies its
    algebra and frequency projection.
    """
    if not (math.isfinite(frequency_hz) and frequency_hz > 0
            and math.isfinite(duration_s) and duration_s > 0 and samples >= 32):
        raise ValueError("Invalid numeric metric arguments")
    qa = []
    qj = []
    qf = []
    for k in range(samples):
        tau = ((k + 0.5) / samples - 0.5) * duration_s
        qa.append(-math.pi * frequency_hz * tau**2 / C_M_PER_S)
        qj.append(-math.pi * frequency_hz * tau**3 / (3.0 * C_M_PER_S))
        qf.append(2.0 * math.pi * tau)

    def cov(x: list[float], y: list[float]) -> float:
        xm = math.fsum(x) / samples
        ym = math.fsum(y) / samples
        return math.fsum((u-xm)*(v-ym) for u, v in zip(x,y)) / samples

    gff = cov(qf, qf)
    gaa = cov(qa, qa) - cov(qa, qf)**2 / gff
    gaj = cov(qa, qj) - cov(qa, qf)*cov(qj, qf) / gff
    gjj = cov(qj, qj) - cov(qj, qf)**2 / gff
    return gaa, gaj, gjj


def coherent_power_loss(
    frequency_hz: float, duration_s: float, delta_a: float, delta_j: float,
    samples: int = 4096
) -> float:
    """Independent numerical coherent-power loss after linear phase detrending.

    Linear phase fitting corresponds to allowing the search to adjust spin
    frequency. This uses least-squares phase projection, which coincides with
    optimal coherent-frequency projection to *leading order* in mismatch.
    For large offsets, do not interpret it as an exact maximum-likelihood
    Fourier search over frequency.
    """
    from .phase import residual_phase_radians

    if samples < 32:
        raise ValueError("At least 32 samples required")
    ProjectedMetric(frequency_hz, duration_s)  # validates both quantities
    taus = [((k+0.5)/samples-0.5)*duration_s for k in range(samples)]
    phases = [residual_phase_radians(t, frequency_hz, delta_a, delta_j) for t in taus]
    mean_tau = math.fsum(taus) / samples
    mean_phase = math.fsum(phases) / samples
    slope = (math.fsum((t-mean_tau)*(p-mean_phase) for t,p in zip(taus,phases))
             / math.fsum((t-mean_tau)**2 for t in taus))
    residuals = [p-mean_phase-slope*(t-mean_tau) for t,p in zip(taus,phases)]
    real = math.fsum(math.cos(p) for p in residuals) / samples
    imag = math.fsum(math.sin(p) for p in residuals) / samples
    return max(0.0, min(1.0, 1.0-real**2-imag**2))
