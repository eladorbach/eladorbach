#!/usr/bin/env python3
"""Small synthetic regression fixtures; never labeled as captured sensor evidence."""
import importlib.util
import pathlib
import struct
import sys
import tempfile
import unittest

import numpy as np

FILE = pathlib.Path(__file__).resolve().parents[1] / "src" / "m1600_offline_qc.py"
spec = importlib.util.spec_from_file_location("m1600_qc", FILE)
qc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qc)


def packet(sequence, dist=500, ring=8, azimuth=0):
    rows = struct.pack(">HHHBB", 0, azimuth, dist, 120, ring) * 160
    return bytes(20) + rows + bytes(3) + bytes([sequence])


def pcap_record(data):
    ip = bytearray(20)
    ip[0] = 0x45
    ip[9] = 17
    ip[12:16] = bytes((192,0,2,1))
    ip[16:20] = bytes((192,0,2,2))
    udp = struct.pack("!HHHH",2368,2368,1312,0)
    ethernet = bytes(12) + bytes((8,0)) + bytes(ip) + udp + data
    return struct.pack("<IIII", 1,0,len(ethernet),len(ethernet)) + ethernet


class M1600QualityTests(unittest.TestCase):
    def test_point_units_azimuth_and_ring(self):
        a,xyz = qc.decode([packet(0,dist=500,ring=8,azimuth=0)])
        self.assertEqual(len(xyz), 160)
        np.testing.assert_allclose(xyz[0], [0,2,0], rtol=0,atol=1e-12)
        b,xyz = qc.decode([packet(0,dist=500,ring=8,azimuth=9000)])
        np.testing.assert_allclose(xyz[0], [2,0,0], rtol=0,atol=1e-12)
        c,xyz = qc.decode([packet(0,dist=500,ring=16)])
        self.assertEqual(len(xyz), 0)

    def test_pcap_framing(self):
        body = struct.pack("<IHHIIII",0xA1B2C3D4,2,4,0,0,65535,1)
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "safe_fixture.pcap"
            p.write_bytes(body+b"".join(pcap_record(packet(s)) for s in [250,251,1,2]))
            frames = qc.load_pcap_frames(p,source_ip="192.0.2.1")
            self.assertEqual([len(x) for x in frames],[2,2])
            self.assertEqual(len(qc.load_pcap_frames(p,source_ip="192.0.2.55")),0)

    def test_angular_cell_bins(self):
        r,_ = qc.decode([packet(1,dist=500,ring=8,azimuth=999)])
        a,c = qc.angular_grid(r)
        k=8*qc.CELLS_PER_RING+99
        self.assertEqual(int(c[k]),160)
        self.assertAlmostEqual(a[k],2.0,places=10)
        self.assertTrue(np.isnan(a[0]))

    def test_plane_candidate_with_outliers(self):
        rng=np.random.RandomState(53)
        xy=rng.uniform(-1,1,(1000,2))
        plane=np.column_stack((xy,2 + rng.normal(0,.004,len(xy))))
        outliers=np.column_stack((rng.uniform(-1,1,(160,2)),rng.uniform(2.25,2.75,160)))
        points=np.vstack((plane,outliers))
        res=qc.planar_candidate(points,seed=7)
        self.assertIsNotNone(res)
        self.assertGreater(res["support_pct"],75)
        self.assertLess(res["thresholded_rms_mm"],10)

    def test_percentiles_and_empty(self):
        v=qc.percentile_dict(np.array([0.,.001,.002,.003,.004]))
        self.assertEqual(v["count"],5)
        self.assertEqual(v["p50_mm"],2.)
        self.assertEqual(qc.percentile_dict([])["count"],0)

    def test_depth_edge_heuristic_does_not_cross_rings(self):
        bins=qc.CELLS_PER_RING
        grid=np.full((16,bins),np.nan)
        grid[3,200:204]=[2.,2.,3.,3.]
        grid[4,200:204]=[4.,4.,4.,4.]
        risk=qc.boundary_risk_from_training_grid(grid.ravel(),10,depth_jump_m=.1).reshape(16,bins)
        self.assertTrue(risk[3,201])
        self.assertTrue(risk[3,202])
        self.assertFalse(risk[3,200])
        self.assertFalse(risk[4,201])
        self.assertEqual(int(risk.sum()),2)

    def test_malformed_capture_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)/"bad.pcap"
            p.write_bytes(b"broken")
            with self.assertRaises(ValueError):
                qc.load_pcap_frames(p)


if __name__ == "__main__":
    unittest.main()
