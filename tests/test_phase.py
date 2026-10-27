import math
import unittest

from pulsejet_bank.phase import (
    acceleration_at_start, arrival_time_seconds, centered_time,
    delay_seconds, phase_radians, residual_phase_radians, C_M_PER_S,
)


class PhaseConventionsTest(unittest.TestCase):
    def test_midpoint_and_start_acceleration_transform(self):
        T = 505.2902701172523
        a_mid, jerk = -235.0, -0.25
        self.assertAlmostEqual(centered_time(T/2, T), 0.0)
        self.assertAlmostEqual(centered_time(0, T), -T/2)
        a_start = acceleration_at_start(a_mid, jerk, T)
        self.assertAlmostEqual(a_start, a_mid-jerk*T/2)
        self.assertAlmostEqual(a_start+jerk*T/2, a_mid)

    def test_gpu_arrival_time_model(self):
        for tau in (-252.6, 0.0, 252.6):
            a,j = -235.0,-0.25
            expected_shift = (a*tau*tau/2 + j*tau**3/6)/C_M_PER_S
            self.assertAlmostEqual(arrival_time_seconds(tau,a,j)-tau,expected_shift,places=12)
            self.assertAlmostEqual(delay_seconds(tau,a,j),expected_shift,places=12)
        self.assertEqual(arrival_time_seconds(0,123,0.42),0)

    def test_sign_and_leading_order_phase(self):
        f,t,a,j = 383.0,90.0,-235.0,-0.25
        baseline = phase_radians(t,f,0,0)
        correction = phase_radians(t,f,a,j)-baseline
        predicted = -2*math.pi*f*delay_seconds(t,a,j)
        self.assertAlmostEqual(correction,predicted,places=9)
        self.assertAlmostEqual(residual_phase_radians(t,f,a,j),predicted,places=12)

    def test_bad_duration(self):
        with self.assertRaises(ValueError):
            centered_time(0,-1)
        with self.assertRaises(ValueError):
            acceleration_at_start(0,0,0)


if __name__ == "__main__":
    unittest.main()
