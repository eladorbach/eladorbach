#!/usr/bin/env python3
"""Only synthetic timestamps; camera samples and LiDAR payload never touched."""
import importlib.util
import pathlib
import unittest

p=pathlib.Path(__file__).resolve().parents[1]/"src"/"host_time_pairing.py"
spec=importlib.util.spec_from_file_location("pair",p)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def make(rate,duration=2.0):
    return [(i/rate,i/rate,1) for i in range(int(duration*rate)+1)]


class HostPairTests(unittest.TestCase):
    def test_matching_30fps_to_20hz_hosts_has_small_nearest_gap(self):
        r=mod.host_stamp_pairing(make(20),make(30))
        self.assertGreater(r["lidar_scans_compared"],30)
        self.assertLessEqual(r["nearest_camera_stamp_absolute_ms_p95"],17.0)
        self.assertIn("NOT sensor",r["meaning"])

    def test_5fps_preview_has_more_matching_ambiguity(self):
        r=mod.host_stamp_pairing(make(20),make(5))
        self.assertGreaterEqual(r["nearest_camera_stamp_absolute_ms_p95"],90.0)

    def test_missing_overlap_does_not_guess(self):
        r=mod.host_stamp_pairing([(5.,5.,1),(5.05,5.05,1)],make(20))
        self.assertEqual(r["lidar_scans_compared"],0)
        self.assertEqual(r["reason"],"no_host_time_overlap")


if __name__=="__main__":
    unittest.main()
