"""PULSEJET-compatible midpoint phase conventions (leading order in v/c).

The GPU's include/transforms/polynomial_timing.hpp maps an emitted sample at
time tau relative to the FFT midpoint to observed arrival time

    t_arr = tau + [a*tau**2/2 + j*tau**3/6] / c .

An observed pulse train evaluated at arrival time has phase, to first order
in the propagation delay,

    phi_arr(tau) ~= 2*pi*f*[tau - (a*tau**2/2+j*tau**3/6)/c].

Signs therefore agree with the arrival-time resampler when interpreted
consistently; the search parameters a and j are MIDPOINT values.
"""
import math

C_M_PER_S = 299_792_458.0


def centered_time(time_since_start_s: float, duration_s: float) -> float:
    """Convert elapsed time since segment start into midpoint offset."""
    if duration_s <= 0 or not math.isfinite(duration_s):
        raise ValueError("duration_s must be finite and positive")
    return time_since_start_s - 0.5 * duration_s


def delay_seconds(tau_s: float, acceleration: float, jerk: float) -> float:
    """Propagation delay in seconds at relative time tau_s."""
    return (0.5 * acceleration * tau_s**2
            + jerk * tau_s**3 / 6.0) / C_M_PER_S


def arrival_time_seconds(tau_s: float, acceleration: float, jerk: float) -> float:
    """PULSEJET GPU's continuous (pre-quantized) time-warp model."""
    return tau_s + delay_seconds(tau_s, acceleration, jerk)


def phase_radians(
    tau_s: float, frequency_hz: float, acceleration: float, jerk: float
) -> float:
    """Leading-order arrival-time phase, referenced to segment midpoint."""
    return 2.0 * math.pi * frequency_hz * (
        tau_s - delay_seconds(tau_s, acceleration, jerk)
    )


def residual_phase_radians(
    tau_s: float, frequency_hz: float, delta_acceleration: float, delta_jerk: float
) -> float:
    """Residual phase from template-minus-signal parameter offsets.

    The overall sign has no effect on coherent power mismatch.
    """
    return -2.0 * math.pi * frequency_hz * delay_seconds(
        tau_s, delta_acceleration, delta_jerk
    )


def acceleration_at_start(acceleration_at_midpoint: float, jerk: float, duration_s: float) -> float:
    """Convert midpoint acceleration to start acceleration: a(0)=a_mid-j*T/2."""
    if duration_s <= 0 or not math.isfinite(duration_s):
        raise ValueError("duration_s must be finite and positive")
    return acceleration_at_midpoint - 0.5 * jerk * duration_s
