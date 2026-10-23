#!/usr/bin/env python3
"""Evaluate full-wall trial *readiness*, not vendor range accuracy.

This does not certify a surface as planar or independently measured.
Metrics and pass/fail gates are predeclared, independent of observed trials.
"""
import argparse
import hashlib
import json
import pathlib


def evaluate(capture, plane, pcap_sha_actual=None):
    criteria={}
    def check(name, condition, measured, expected):
        criteria[name]={"pass":bool(condition),"measured":measured,"expected":expected}
    packets=int(capture.get("verified_packets",0))
    check("genuine_M1600_packet_count",packets>=1500,packets,">=1500")
    observed=int(capture.get("frame_boundaries_observed",0))
    check("scan_boundaries",observed>=10,observed,">=10")
    discontinuities=int(capture.get("sequence_discontinuities",-1))
    check("packet_sequence",discontinuities==0,discontinuities,"zero observed discontinuities")
    check("bounded_recording",not capture.get("size_limit_hit",True),capture.get("size_limit_hit"),False)
    first=capture.get("complete_interior_frame_packet_count_min")
    last=capture.get("complete_interior_frame_packet_count_max")
    check("frame_packet_coverage",first is not None and last is not None and
          180<=first<=last<=240,[first,last],"180..240 per interior frame (current observed mode)")
    if pcap_sha_actual is not None:
        expected_sha=capture.get("pcap_sha256")
        check("capture_integrity_sha256",pcap_sha_actual==expected_sha,
              pcap_sha_actual==expected_sha,"exact capture hash match")
    check("benchmark_provenance",plane.get("provenance")=="READ_ONLY_REAL_M1600_PACKET_CAPTURE",
          plane.get("provenance"),"READ_ONLY_REAL_M1600_PACKET_CAPTURE")
    check("benchmark_same_capture",plane.get("pcap_sha256")==capture.get("pcap_sha256"),
          plane.get("pcap_sha256")==capture.get("pcap_sha256"),True)
    label=plane.get("surface_label")
    wall_operator_claim=(label=="bare_wall" and plane.get("operator_has_verified_surface") is True)
    check("operator_identified_bare_wall",wall_operator_claim,label,"bare_wall with operator verification")
    trained=int(plane.get("training_frames",0))
    heldout=int(plane.get("heldout_frames",0))
    check("independent_scans_train_and_holdout",trained>=5 and heldout>=5,[trained,heldout],"both >=5")
    support=float(plane.get("train_plane",{}).get("training_support_fraction_40mm",0))
    check("training_roi_planar_support",support>=.80,round(support,4),">=0.80 on predefined ROI")
    p95=plane.get("heldout",{}).get("heldout_absolute_residual_mm_p50_p90_p95_p99",[float("inf")]*4)[2]
    check("heldout_hypothesis_p95",p95<=40.0,p95,"<=40mm exploratory acceptance, NOT absolute accuracy")
    span=plane.get("train_plane",{}).get("training_robust_plane_span_5to95_m",[0,0])
    check("visible_surface_extent",len(span)==2 and min(span)>=.5,
          span,"both plane axes span >=0.5m")
    actual_ok=all(x["pass"] for x in criteria.values())
    return {"schema":"m1600-wall-acceptance/1",
            "ready_for_next_wall_retest":actual_ok,
            "physical_absolute_range_accuracy_certified":False,
            "camera_lidar_calibration_certified":False,
            "geometry_gate_experimental":True,
            "criteria":criteria,
            "gating_policy":"Fixed indicative criteria; must record actual flat wall selection. No absolute external ground truth."}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--capture-receipt",type=pathlib.Path,required=True)
    p.add_argument("--geometry-report",type=pathlib.Path,required=True)
    p.add_argument("--output",type=pathlib.Path,required=True)
    p.add_argument("--strict",action="store_true",help="nonzero exit status if acceptance failed")
    a=p.parse_args()
    capture=json.loads(a.capture_receipt.read_text())
    geometry=json.loads(a.geometry_report.read_text())
    raw=pathlib.Path(capture.get("pcap_path_local_only",""))
    sha=None
    if raw.is_file():
        h=hashlib.sha256()
        with raw.open("rb") as stream:
            for part in iter(lambda:stream.read(1024*1024),b""):h.update(part)
        sha=h.hexdigest()
    verdict=evaluate(capture,geometry,sha)
    verdict["pcap_hash_reverified"]=sha is not None
    a.output.write_text(json.dumps(verdict,indent=2)+"\n")
    print(json.dumps({"ready_for_next_wall_retest":verdict["ready_for_next_wall_retest"],
                      "gates":[[k,v["pass"]] for k,v in verdict["criteria"].items()],
                      "absolute_accuracy_certified":False},indent=2))
    if a.strict and not verdict["ready_for_next_wall_retest"]:
        raise SystemExit(2)


if __name__=="__main__":
    main()
