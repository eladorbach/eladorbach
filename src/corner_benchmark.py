#!/usr/bin/env python3
"""Prepares a two-plane corner test using manual, independently held-out ROIs.

Never infers physical edge truth, even when two planar hypotheses intersect.
Operates only on existing private M1600 PCAP; no sensor commands or pictures.
"""
import argparse
import hashlib
import json
import pathlib

import numpy as np

import full_wall_benchmark as wall
import m1600_offline_qc as qc


def intersection(model_a, model_b):
    n1=np.asarray(model_a["normal_xyz"],dtype=float)
    n2=np.asarray(model_b["normal_xyz"],dtype=float)
    d=np.cross(n1,n2)
    size=float(np.linalg.norm(d))
    angle=float(np.degrees(np.arccos(np.clip(abs(np.dot(n1,n2)),-1.,1.))))
    if size<1e-3:
        return {"plane_normal_angle_deg":round(angle,3),
                "intersection_valid":False,
                "reason":"nearly_parallel_planes"}
    direction=d/size
    # Closest-to-sensor point on intersection, not a measured edge pixel.
    m=np.stack((n1,n2,direction),axis=0)
    offsets=np.array([-model_a["offset_m"],-model_b["offset_m"],0.])
    point=np.linalg.solve(m,offsets)
    return {"plane_normal_angle_deg":round(angle,3),
            "intersection_valid":True,
            "model_intersection_closest_origin_m":np.round(point,5).tolist(),
            "model_intersection_direction_xyz":np.round(direction,5).tolist(),
            "caveat":"Mathematical intersection of two estimated infinite planes only. NOT observed edge location."}


def run(pcap,roi_a,roi_b):
    if roi_a["surface_label"]!= "corner_a" or roi_b["surface_label"]!="corner_b":
        raise ValueError("manually label disjoint adjacent faces corner_a and corner_b")
    a=wall.validate_roi(roi_a)
    b=wall.validate_roi(roi_b)
    frames=qc.load_pcap_frames(pcap)
    fa=wall.benchmark(frames,a,sample_frames=12)
    fb=wall.benchmark(frames,b,sample_frames=12)
    crossed=intersection(fa["train_plane"],fb["train_plane"])
    return {"schema":"m1600-two-plane-corner/1",
            "source_pcap_sha256":hashlib.sha256(pcap.read_bytes()).hexdigest(),
            "face_a_train":fa["train_plane"],
            "face_b_train":fb["train_plane"],
            "face_a_heldout":fa["heldout"],
            "face_b_heldout":fb["heldout"],
            "intersection_model":crossed,
            "corner_truth_verified":False,
            "sharp_edge_location_accuracy_certified":False,
            "limitations":["Both face ROIs are operator-defined; current scene may contain arbitrary surfaces.",
                           "Plane intersection is not a direct observed edge, nor a held-out distance to real corner.",
                           "Edge location accuracy awaits independently measured physical corner."]}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pcap",type=pathlib.Path,required=True)
    p.add_argument("--face-a",type=pathlib.Path,required=True)
    p.add_argument("--face-b",type=pathlib.Path,required=True)
    p.add_argument("--output",type=pathlib.Path,required=True)
    a=p.parse_args()
    report=run(a.pcap,json.loads(a.face_a.read_text()),json.loads(a.face_b.read_text()))
    a.output.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"intersection":report["intersection_model"],
                      "corner_truth_verified":False},indent=2))


if __name__=="__main__":
    main()
