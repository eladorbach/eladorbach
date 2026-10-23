#!/usr/bin/env python3
"""Synthetic fit/holdout tests. These results MUST NOT be published as real walls."""
import importlib.util
import pathlib
import unittest

import numpy as np

PATH=pathlib.Path(__file__).resolve().parents[1]/"src"/"full_wall_benchmark.py"
spec=importlib.util.spec_from_file_location("fullwall",PATH)
wall=importlib.util.module_from_spec(spec)
spec.loader.exec_module(wall)


class WallBenchmarkTests(unittest.TestCase):
    def test_roi_fails_closed(self):
        with self.assertRaises(ValueError):
            wall.validate_roi({"surface_label":"bare_wall"})
        good={"surface_label":"bare_wall","operator_has_verified_surface":False,
              "azimuth_min_deg":30,"azimuth_max_deg":80,
              "elevation_min_deg":-10,"elevation_max_deg":20,
              "range_min_m":.5,"range_max_m":4.}
        self.assertEqual(wall.validate_roi(good),good)
        bad=dict(good,range_min_m=6.,range_max_m=1.)
        with self.assertRaises(ValueError):
            wall.validate_roi(bad)
        bad2=dict(good,surface_label="improper_auto_wall")
        with self.assertRaises(ValueError):
            wall.validate_roi(bad2)

    def test_synthetic_pcap_decoder_to_wall_holdout_end_to_end(self):
        # Synthesized 12 full scans; a plane Y=2m. Not an authentic LiDAR recording.
        import math
        import struct
        import tempfile
        from pathlib import Path
        packet_header=struct.pack("<IHHIIII",0xA1B2C3D4,2,4,0,0,65535,1)
        ip=bytearray(20)
        ip[0]=0x45
        ip[9]=17
        ip[12:16]=bytes((192,0,2,10))
        ip[16:20]=bytes((192,0,2,20))
        udp=struct.pack("!HHHH",2368,2368,1312,0)
        eth=bytes(12)+bytes((8,0))+bytes(ip)+udp
        with tempfile.TemporaryDirectory(prefix="m1600_SYNTHETIC_only_") as directory:
            source=Path(directory)/"synthetic_plane.pcap"
            with source.open("wb") as out:
                out.write(packet_header)
                for frame_id in range(12):
                    for seq in range(210):
                        az=int(1000+3000*seq/209)
                        theta=math.radians(az*.01)
                        returns=[]
                        for j in range(160):
                            ring=j%16
                            el=math.radians(2*ring-16)
                            distance=2./(math.cos(theta)*math.cos(el))
                            units=int(round(distance/.004))
                            returns.append(struct.pack(">HHHBB",0,az,units,110,ring))
                        body=bytes(20)+b"".join(returns)+bytes(3)+bytes((seq,))
                        data=eth+body
                        out.write(struct.pack("<IIII",frame_id+1,seq*5000,len(data),len(data)))
                        out.write(data)
            frames=wall.qc.load_pcap_frames(source)
            self.assertEqual(len(frames),12)
            roi={"surface_label":"bare_wall","operator_has_verified_surface":False,
                 "azimuth_min_deg":9.,"azimuth_max_deg":41.,
                 "elevation_min_deg":-18.,"elevation_max_deg":18.,
                 "range_min_m":1.,"range_max_m":4.}
            result=wall.benchmark(frames,roi)
            self.assertEqual(result["training_frames"],6)
            self.assertEqual(result["heldout_frames"],6)
            self.assertGreater(result["train_plane"]["training_support_fraction_40mm"],.99)
            self.assertLess(result["heldout"]["heldout_absolute_residual_mm_p50_p90_p95_p99"][2],10)
            self.assertEqual(result["surface_label"],"bare_wall")
            self.assertFalse(result["operator_has_verified_surface"])

    def test_heldout_true_synthetic_plane(self):
        rng=np.random.RandomState(11)
        def data(count,sigma):
            x=rng.uniform(-1.5,1.5,count)
            z=rng.uniform(-.8,.8,count)
            y=2.25+rng.normal(0,sigma,count)
            return np.column_stack((x,y,z))
        train=data(3200,.004)
        train[:100,1]+=rng.uniform(.1,.6,100)
        heldout=data(1400,.004)
        model=wall.fit_robust_plane(train)
        self.assertGreater(model["training_support_fraction_40mm"],.90)
        result=wall.evaluate_plane(model,heldout)
        self.assertLess(result["heldout_absolute_residual_mm_p50_p90_p95_p99"][2],11)
        self.assertEqual(result["heldout_points_unconditionally_evaluated"],1400)

    def test_outliers_cannot_be_hidden_in_holdout(self):
        rng=np.random.RandomState(44)
        xyz=np.column_stack((rng.uniform(-1,1,1200),np.full(1200,2.),rng.uniform(-1,1,1200)))
        model=wall.fit_robust_plane(xyz)
        hold=np.copy(xyz)
        hold[::5,1]+=.4
        result=wall.evaluate_plane(model,hold)
        self.assertGreater(result["heldout_residual_over_40mm_pct"],19)
        self.assertGreater(result["heldout_absolute_residual_mm_p50_p90_p95_p99"][2],300)


if __name__=="__main__":
    unittest.main()
