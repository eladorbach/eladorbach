#!/usr/bin/env python3
"""Synthetic finite geometry fixtures for corner workflow."""
import pathlib
import sys
import unittest

import numpy as np

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"src"))
import corner_benchmark as corner


class CornerBenchmarkTest(unittest.TestCase):
    def test_perpendicular_planes_intersection(self):
        a={"normal_xyz":[1.,0.,0.],"offset_m":-2.}
        b={"normal_xyz":[0.,1.,0.],"offset_m":-3.}
        r=corner.intersection(a,b)
        self.assertTrue(r["intersection_valid"])
        self.assertAlmostEqual(r["plane_normal_angle_deg"],90.,places=2)
        np.testing.assert_allclose(r["model_intersection_closest_origin_m"],[2.,3.,0.],atol=1e-4)
        self.assertIn("NOT observed",r["caveat"])

    def test_parallel_surfaces_do_not_create_false_edge(self):
        a={"normal_xyz":[1.,0.,0.],"offset_m":-2.}
        b={"normal_xyz":[1.,0.,0.],"offset_m":-3.}
        r=corner.intersection(a,b)
        self.assertFalse(r["intersection_valid"])
        self.assertEqual(r["reason"],"nearly_parallel_planes")


if __name__=="__main__":
    unittest.main()
