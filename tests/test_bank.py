import hashlib
import math
import tempfile
from pathlib import Path
import unittest

from pulsejet_bank.bank import (
    BankSpec, grid_shape, grid_worst_case_metric_bound, make_grid,
    make_stochastic, metric_coverage, nearest_metric_mismatch, read_bank,
    stochastic_count, write_bank,
)


class BankGenerationTest(unittest.TestCase):
    def setUp(self):
        self.spec = BankSpec(383.,505.2902701172523,-255,-215,-0.4,0.25,0.3)

    def test_grid_rectangle_including_boundaries(self):
        bank=make_grid(self.spec)
        na,nj=grid_shape(self.spec)
        self.assertEqual(len(bank),na*nj)
        self.assertGreaterEqual(na,1)
        self.assertGreaterEqual(nj,1)
        self.assertLessEqual(grid_worst_case_metric_bound(self.spec),self.spec.max_mismatch+1e-12)
        g=self.spec.metric
        for a in [self.spec.a_min,-235,self.spec.a_max]:
            for j in [self.spec.j_min,-.25,0,self.spec.j_max]:
                self.assertLessEqual(nearest_metric_mismatch((a,j),bank,g),.3+1e-12)
        cov = metric_coverage(self.spec,bank,samples=200,seed=23)
        self.assertEqual(cov["fraction_within_target"],1.)
        self.assertLessEqual(cov["worst_corner_metric_mismatch"],.3+1e-12)

    def test_small_boxes_and_single_axis(self):
        spec = BankSpec(100,20,3,3,-0.1,0.1,.1)
        bank = make_grid(spec)
        self.assertTrue(all(a==3 for a,_ in bank))
        self.assertLessEqual(grid_worst_case_metric_bound(spec),0.1+1e-12)

    def test_stochastic_reproducible_and_not_guaranteed(self):
        count = stochastic_count(self.spec,.9)
        self.assertGreaterEqual(count,1)
        left=make_stochastic(self.spec,count=count,seed=321)
        self.assertEqual(left,make_stochastic(self.spec,count=count,seed=321))
        self.assertNotEqual(left,make_stochastic(self.spec,count=count,seed=322))
        self.assertTrue(all(self.spec.a_min <= a <= self.spec.a_max
            and self.spec.j_min <= j <= self.spec.j_max for a,j in left))
        self.assertGreaterEqual(metric_coverage(self.spec,left,samples=200,seed=11)["fraction_within_target"],0)

    def test_strict_two_column_float_roundtrip(self):
        bank=make_grid(self.spec)
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"bank.txt"
            digest=write_bank(path,bank)
            self.assertEqual(digest,hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertEqual(read_bank(path),bank)
            self.assertTrue(all(len(line.split())==2 for line in path.read_text().splitlines()))
            with self.assertRaises(FileExistsError):
                write_bank(path,bank)
            self.assertEqual(write_bank(path,bank,overwrite=True),digest)

    def test_i15_truth_is_covered_without_exact_truth_template(self):
        """Control example: make a genuine off-grid injected source."""
        bank = make_grid(self.spec)
        truth = (-235.0,-0.25)  # W3/I15; explicitly NOT inserted
        self.assertNotIn(truth,bank)
        mismatch = nearest_metric_mismatch(truth,bank,self.spec.metric)
        self.assertAlmostEqual(mismatch,0.16431401102179768,places=12)
        self.assertLessEqual(mismatch,self.spec.max_mismatch)

    def test_invalid_inputs_rejected(self):
        with self.assertRaises(ValueError):
            BankSpec(383,505,2,-2,-1,1,.3)
        with self.assertRaises(ValueError):
            BankSpec(383,505,-2,2,-1,1,1.)
        with self.assertRaises(ValueError):
            stochastic_count(self.spec,1.0)
        with self.assertRaises(ValueError):
            make_stochastic(self.spec,count=0)


if __name__ == "__main__":
    unittest.main()
