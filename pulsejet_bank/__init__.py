"""Midpoint-referenced polynomial acceleration/jerk bank construction.

Version 0.1.0: leading-order coherent phase metric for a searched spin
frequency. Not a model of the pipeline's harmonic-summed detection statistic.
"""
from .metric import ProjectedMetric
from .bank import BankSpec, make_grid, make_stochastic, metric_coverage, write_bank

__all__ = [
    "ProjectedMetric", "BankSpec", "make_grid", "make_stochastic",
    "metric_coverage", "write_bank",
]
__version__ = "0.1.0"
