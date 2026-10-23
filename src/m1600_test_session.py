#!/usr/bin/env python3
"""One-command bounded M1600 wall session. No camera use, sensor control or downloads.

Commands:
  preflight: validate configuration and local dependencies, no sensor access.
  replay: replay analysis from an existing private PCAP, no sensor access.
  capture: obtain independent passive trials + run same analysis/acceptance.
Requires operator-verified flat wall & measured ROI in later real full-wall stage.
"""
import argparse
import datetime
import hashlib
import importlib.util
import json
import os
import pathlib
import time

import numpy as np

DIR=pathlib.Path(__file__).resolve().parent
EVIDENCE=pathlib.Path("/home/sticker/Waymo_Lidar_Capture/ros_fusion/evidence")


def load(local, name):
    spec=importlib.util.spec_from_file_location(name,DIR/local)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cap=load("m1600_capture_verified.py","m1600_capture_verified")
qc=load("m1600_offline_qc.py","m1600_offline_qc")
wall=load("full_wall_benchmark.py","full_wall_benchmark")
gate=load("m1600_session_gate.py","m1600_session_gate")


def file_sha(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for part in iter(lambda:f.read(1024*1024),b""):h.update(part)
    return h.hexdigest()


def preflight(roi_path, mode, scene):
    roi=wall.validate_roi(json.loads(roi_path.read_text()))
    label=roi["surface_label"]
    if scene=="wall_operator_labeled":
        if not (label=="bare_wall" and roi.get("operator_has_verified_surface") is True):
            raise ValueError("wall mode requires bare_wall ROI with operator_has_verified_surface=true; do not claim physical truth automatically")
    elif label=="bare_wall" and roi.get("operator_has_verified_surface") is True:
        if mode=="capture":
            raise ValueError("operator-labeled wall ROI cannot be used with uncontrolled capture")
    problems=[]
    if mode=="capture" and os.geteuid()!=0:
        problems.append("passive AF_PACKET capture requires authorized local elevated execution")
    if mode=="capture" and not pathlib.Path("/sys/class/net/eth0").exists():
        problems.append("eth0 missing")
    if not EVIDENCE.is_dir():
        problems.append("private evidence directory missing")
    if pathlib.Path("/home/sticker/Waymo_Lidar_Capture/ros_fusion").resolve() not in roi_path.resolve().parents:
        problems.append("ROI must be stored inside project root")
    if problems:
        raise RuntimeError("; ".join(problems))
    return {"result":"PREFLIGHT_OK", "scene":scene, "roi_label":label,
            "roi_sha256":file_sha(roi_path), "mode":mode,
            "camera_calibrated":False,"LiDAR_absolute_accuracy_certified":False,
            "note":"A physically aligned flat wall cannot be verified by this preflight."}


def analyze(pcap, roi, capture_receipt, tag, live_capture_verified=False):
    frames=qc.load_pcap_frames(pcap)
    dataset=wall.benchmark(frames,roi,12)
    dataset["pcap_sha256"]=file_sha(pcap)
    dataset["provenance"]=("READ_ONLY_REAL_M1600_PACKET_CAPTURE" if live_capture_verified
                           else "READ_ONLY_PCAP_ORIGIN_NOT_EXTERNALLY_VERIFIED")
    target=EVIDENCE/(tag+"_GEOMETRY.json")
    with target.open("x") as f:
        json.dump(dataset,f,indent=2)
        f.write("\n")
    result=gate.evaluate(capture_receipt,dataset,dataset["pcap_sha256"])
    target_gate=EVIDENCE/(tag+"_ACCEPTANCE.json")
    with target_gate.open("x") as f:
        json.dump(result,f,indent=2)
        f.write("\n")
    if os.geteuid()==0:
        os.chown(str(target),1000,1000)
        os.chown(str(target_gate),1000,1000)
    return {"pcap_sha256":dataset["pcap_sha256"],
            "pcap_local_only":str(pcap),
            "geometry_private":str(target),
            "gate_private":str(target_gate),
            "frame_count":len(frames),
            "heldout_p95_mm":dataset["heldout"]["heldout_absolute_residual_mm_p50_p90_p95_p99"][2],
            "candidate_plane_normal_xyz":dataset["train_plane"]["normal_xyz"],
            "candidate_plane_offset_m":dataset["train_plane"]["offset_m"],
            "acceptance_pass":result["ready_for_next_wall_retest"],
            "reasons_not_passed":[k for k,v in result["criteria"].items() if not v["pass"]]}


def main():
    os.umask(0o077)  # private numerical geometry and capture receipts
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode",choices=("preflight","replay","capture"))
    p.add_argument("--roi-json",type=pathlib.Path,required=True)
    p.add_argument("--scene",choices=("uncontrolled","wall_operator_labeled"),default="uncontrolled")
    p.add_argument("--pcap",type=pathlib.Path,help="for replay only")
    p.add_argument("--seconds",type=int,default=3)
    p.add_argument("--trials",type=int,default=1)
    p.add_argument("--max-mib",type=int,default=24)
    a=p.parse_args()
    if a.mode=="capture" and not (1<=a.trials<=3 and 2<=a.seconds<=10 and 8<=a.max_mib<=64):
        raise ValueError("capture limited to 1..3 trials, 2..10 sec, 8..64MiB each")
    if a.mode=="replay" and not (a.pcap and a.pcap.is_file()):
        raise ValueError("replay requires known recorded --pcap")
    pflight=preflight(a.roi_json,a.mode,a.scene)
    if a.mode=="preflight":
        print(json.dumps(pflight,indent=2))
        return
    roi=json.loads(a.roi_json.read_text())
    name="M1600_SESSION_"+datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    receipts=[]
    for i in range(a.trials if a.mode=="capture" else 1):
        if a.mode=="capture":
            raw=cap.bounded_capture(a.seconds,a.max_mib,a.scene)
            pcap=pathlib.Path(raw["pcap_path_local_only"])
        else:
            pcap=a.pcap
            # Replay has genuine PCAP but no new passive hardware capture receipt.
            # It must not pretend to pass packet-capture gate.
            raw={"verified_packets":0,"frame_boundaries_observed":0,
                 "sequence_discontinuities":-1,"size_limit_hit":True,
                 "pcap_sha256":file_sha(pcap)}
        trialtag=f"{name}_T{i+1}"
        receipt=analyze(pcap,roi,raw,trialtag,live_capture_verified=(a.mode=="capture"))
        receipt["trial"]=i+1
        receipt["live_capture_performed"]=a.mode=="capture"
        receipts.append(receipt)
    paired=[]
    for i in range(len(receipts)):
        for j in range(i+1,len(receipts)):
            x=receipts[i];y=receipts[j]
            n=np.asarray(x["candidate_plane_normal_xyz"])
            m=np.asarray(y["candidate_plane_normal_xyz"])
            angle=float(np.degrees(np.arccos(np.clip(abs(n@m),-1,1))))
            paired.append({"trial_a":i+1,"trial_b":j+1,
                "candidate_plane_normal_angle_deg":round(angle,4),
                "candidate_plane_offset_delta_mm":round(1000*abs(x["candidate_plane_offset_m"]-y["candidate_plane_offset_m"]),3)})
    report={"schema":"m1600-session/1",
            "at_utc":name,"mode":a.mode,"scene":a.scene,
            "cross_trial_exploratory_plane_repeatability":paired,
            "preflight":pflight,"trial_results":receipts,
            "all_wall_acceptance_pass":all(x["acceptance_pass"] for x in receipts),
            "absolute_range_accuracy_certified":False,
            "IMX252_extrinsic_certified":False,
            "note":"Satisfying exploratory plane gates is not an absolute reference measurement."}
    target=EVIDENCE/(name+"_SUMMARY.json")
    with target.open("x") as f:
        json.dump(report,f,indent=2)
        f.write("\n")
    if os.geteuid()==0:
        os.chown(str(target),1000,1000)
    print(json.dumps({"private_session_report":str(target),
        "mode":a.mode,"trials":len(receipts),"wall_gate_passes":[x["acceptance_pass"] for x in receipts],
        "frame_counts":[x["frame_count"] for x in receipts],
        "heldout_p95_mm":[x["heldout_p95_mm"] for x in receipts],
        "absolute_accuracy_certified":False},indent=2))


if __name__=="__main__":
    main()
