#!/usr/bin/env python3
"""Synthetic-only gate contract tests; no hardware or genuine wall claims."""
import copy
import importlib.util
import pathlib
import unittest

file=pathlib.Path(__file__).resolve().parents[1]/"src"/"m1600_session_gate.py"
s=importlib.util.spec_from_file_location("m1600_gate",file)
g=importlib.util.module_from_spec(s)
s.loader.exec_module(g)


def known_good():
    capture={"verified_packets":14000,"frame_boundaries_observed":55,
             "sequence_discontinuities":0,"size_limit_hit":False,
             "complete_interior_frame_packet_count_min":209,
             "complete_interior_frame_packet_count_max":210,
             "pcap_sha256":"testhash"}
    benchmark={"provenance":"READ_ONLY_REAL_M1600_PACKET_CAPTURE",
               "pcap_sha256":"testhash",
               "surface_label":"bare_wall","operator_has_verified_surface":True,
               "training_frames":6,"heldout_frames":6,
               "train_plane":{"training_support_fraction_40mm":.94,
                              "training_robust_plane_span_5to95_m":[1.2,.9]},
               "heldout":{"heldout_absolute_residual_mm_p50_p90_p95_p99":[2,4,10,25]}}
    return capture,benchmark


class GateTest(unittest.TestCase):
    def test_synthetic_contract_can_pass_without_certifying_absolute_accuracy(self):
        c,b=known_good()
        r=g.evaluate(c,b,"testhash")
        self.assertTrue(r["ready_for_next_wall_retest"])
        self.assertFalse(r["physical_absolute_range_accuracy_certified"])
        self.assertFalse(r["camera_lidar_calibration_certified"])

    def test_real_scene_not_assumed_flat(self):
        c,b=known_good()
        b["surface_label"]="uncontrolled_candidate"
        b["operator_has_verified_surface"]=False
        result=g.evaluate(c,b,"testhash")
        self.assertFalse(result["ready_for_next_wall_retest"])
        self.assertFalse(result["criteria"]["operator_identified_bare_wall"]["pass"])

    def test_corrupt_or_missing_packets_do_not_pass(self):
        c,b=known_good()
        c["sequence_discontinuities"]=3
        r=g.evaluate(c,b,"testhash")
        self.assertFalse(r["ready_for_next_wall_retest"])
        c["sequence_discontinuities"]=0
        self.assertFalse(g.evaluate(c,b,"tampered")["ready_for_next_wall_retest"])

    def test_outliers_cannot_disappear(self):
        c,b=known_good()
        b["heldout"]["heldout_absolute_residual_mm_p50_p90_p95_p99"][2]=90
        r=g.evaluate(c,b,"testhash")
        self.assertFalse(r["criteria"]["heldout_hypothesis_p95"]["pass"])


if __name__=="__main__":
    unittest.main()
