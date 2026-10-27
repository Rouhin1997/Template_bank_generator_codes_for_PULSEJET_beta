import math
import unittest

from pulsejet_bank.metric import (
    ProjectedMetric, projected_metric_numerical, coherent_power_loss,
)


class MidpointMetricTest(unittest.TestCase):
    def test_analytic_and_independent_numeric_schur(self):
        for f,T in [(247.,252.645135), (383.,505.2902701172523), (400.,893.)]:
            analytical = ProjectedMetric(f,T)
            gaa,gaj,gjj = projected_metric_numerical(f,T,8192)
            self.assertAlmostEqual(gaa/analytical.gaa,1.0,delta=4e-6)
            self.assertAlmostEqual(gjj/analytical.gjj,1.0,delta=1e-5)
            self.assertLess(abs(gaj)/math.sqrt(analytical.gaa*analytical.gjj),1e-11)

    def test_frequency_and_duration_scaling(self):
        m1 = ProjectedMetric(200,500)
        m2 = ProjectedMetric(400,500)
        self.assertAlmostEqual(m2.gaa/m1.gaa,4)
        self.assertAlmostEqual(m2.gjj/m1.gjj,4)
        longer = ProjectedMetric(200,1000)
        self.assertAlmostEqual(longer.gaa/m1.gaa,16)
        self.assertAlmostEqual(longer.gjj/m1.gjj,64)

    def test_coherent_loss_matches_local_metric_after_frequency_fit(self):
        for frequency,T in [(247.,253.),(383.,505.29027),(400.,893.)]:
            g = ProjectedMetric(frequency,T)
            for target in [0.005,0.025,0.07]:
                da = math.sqrt(target/g.gaa)
                dj = math.sqrt(target/g.gjj)
                for a,j in [(da,0.),(0.,dj),(da/math.sqrt(2),dj/math.sqrt(2))]:
                    predicted = g.mismatch(a,j)
                    numerical = coherent_power_loss(frequency,T,a,j,samples=4096)
                    self.assertLess(
                        abs(numerical-predicted),0.012,
                        msg=f"f={frequency} T={T} a={a} j={j}: {predicted} vs {numerical}"
                    )

    def test_cross_term_vanishes_at_midpoint(self):
        m = ProjectedMetric(383,505)
        self.assertEqual(m.gaj,0)
        a,j = 20.,0.07
        self.assertAlmostEqual(m.mismatch(a,j),m.mismatch(-a,j))
        self.assertAlmostEqual(m.mismatch(a,j),m.mismatch(a,-j))

    def test_invalid_metric(self):
        for f,T in [(0,10),(-1,10),(1,0),(float("nan"),100)]:
            with self.assertRaises(ValueError):
                ProjectedMetric(f,T)


if __name__ == "__main__":
    unittest.main()
