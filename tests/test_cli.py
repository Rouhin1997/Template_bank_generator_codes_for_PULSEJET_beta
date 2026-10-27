import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class CommandLineTest(unittest.TestCase):
    def run_cli(self,*extra):
        return subprocess.run(
            [sys.executable,"-m","pulsejet_bank",
             "--frequency-hz","383","--duration-s","505.2902701172523",
             "--a-min","-255","--a-max","-215",
             "--j-min","-0.4","--j-max","0.25",
             "--mismatch","0.3",*extra],
            capture_output=True,text=True,
        )

    def test_complete_output_and_provenance(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)
            ret=self.run_cli("--output",str(p/"bank.txt"),"--report",str(p/"report.json"),"--validation-points","250")
            self.assertEqual(ret.returncode,0,ret.stderr)
            summary=json.loads(ret.stdout)
            report=json.loads((p/"report.json").read_text())
            self.assertEqual(summary,report)
            self.assertEqual(summary["template_count"],len((p/"bank.txt").read_text().splitlines()))
            self.assertEqual(report["validation"]["fraction_within_target"],1.0)
            self.assertLessEqual(report["construction"]["grid_worst_case_quadratic_mismatch_bound"],0.3)
            again=self.run_cli("--output",str(p/"bank.txt"))
            self.assertNotEqual(again.returncode,0)
            self.assertIn("Output already exists",again.stderr)

    def test_stochastic_bank_count(self):
        with tempfile.TemporaryDirectory() as td:
            ret=self.run_cli("--method","stochastic","--templates","33","--seed","7",
                             "--output",str(Path(td)/"bank.txt"),"--validation-points","30")
            self.assertEqual(ret.returncode,0,ret.stderr)
            self.assertEqual(json.loads(ret.stdout)["template_count"],33)

    def test_invalid_grid_override(self):
        with tempfile.TemporaryDirectory() as td:
            ret=self.run_cli("--templates","100","--output",str(Path(td)/"bank.txt"))
            self.assertNotEqual(ret.returncode,0)
            self.assertIn("only valid",ret.stderr)


if __name__ == "__main__":
    unittest.main()
