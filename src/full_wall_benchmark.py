#!/usr/bin/env python3
"""Measured-wall / planar-ROI benchmark. Physical truth is never inferred.

Planar 3D geometry is fitted from one half of independently recorded frames
and evaluated on the other half without post-fit truncation. ROI boundaries
come from explicitly saved user/operator annotations in LiDAR polar coords.
Raw PCAP stays private; only numerical statistics go to JSON.
"""
import argparse
import hashlib
import importlib.util
import json
import math
import pathlib
import time

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("offline_qc", HERE/"m1600_offline_qc.py")
qc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(qc)


def validate_roi(roi):
    """Validate manually predeclared polar patch bounds; no auto-labeling."""
    keys=("azimuth_min_deg","azimuth_max_deg","elevation_min_deg",
          "elevation_max_deg","range_min_m","range_max_m")
    if any(k not in roi for k in keys):
        raise ValueError("ROI must specify azimuth, elevation and range bounds")
    vals=[float(roi[k]) for k in keys]
    if not (0<=vals[0]<vals[1]<=360):
        raise ValueError("bad azimuth ROI")
    if not (-90<=vals[2]<vals[3]<=90):
        raise ValueError("bad elevation ROI")
    if not (0.1<=vals[4]<vals[5]<=200):
        raise ValueError("bad range ROI")
    if roi.get("surface_label") not in ("uncontrolled_candidate","bare_wall","floor","corner_a","corner_b"):
        raise ValueError("surface label must be explicit")
    if not isinstance(roi.get("operator_has_verified_surface",False),bool):
        raise ValueError("operator_has_verified_surface must be boolean")
    return roi


def select_roi(raw, xyz, roi):
    """Use measured scanner polar angles/range rather than postfit plane residual."""
    az=raw["azm"].astype(np.float64)*0.01
    rad=np.sqrt(np.sum(xyz*xyz,axis=1))
    elev=np.degrees(np.arctan2(xyz[:,2],np.sqrt(xyz[:,0]**2+xyz[:,1]**2)))
    return ((az>=roi["azimuth_min_deg"]) & (az<=roi["azimuth_max_deg"]) &
            (elev>=roi["elevation_min_deg"]) & (elev<=roi["elevation_max_deg"]) &
            (rad>=roi["range_min_m"]) & (rad<=roi["range_max_m"]))


def fit_robust_plane(train_xyz, threshold=0.04, seed=45, iterations=200):
    """Robust candidate fit on training points only; no supervised ground truth."""
    if len(train_xyz)<300:
        raise ValueError("ROI contains insufficient training points")
    rng=np.random.RandomState(seed)
    s=train_xyz[rng.choice(len(train_xyz),min(7000,len(train_xyz)),replace=False)]
    best=0;support=None
    for _ in range(iterations):
        a,b,c=s[rng.choice(len(s),3,replace=False)]
        normal=np.cross(b-a,c-a)
        length=np.linalg.norm(normal)
        if length<1.e-8:continue
        normal/=length
        hits=np.abs((s-a).dot(normal))<=threshold
        count=int(np.count_nonzero(hits))
        if count>best:
            best=count;support=s[hits]
    if support is None or len(support)<250:
        raise ValueError("no stable planar hypothesis")
    center=support.mean(axis=0)
    _,_,axes=np.linalg.svd(support-center,full_matrices=False)
    normal=axes[-1]
    if normal[0]<0:
        normal=-normal
    offset=-normal@center
    training_distances=np.abs(train_xyz@normal+offset)
    train_support=float(np.mean(training_distances<=threshold))
    # The plotted plane extents are a diagnostic only, not real wall dimensions.
    inliers=train_xyz[training_distances<=threshold]
    span=np.percentile(inliers@axes[:2].T,[5,95],axis=0)
    return {
        "normal_xyz":[round(float(x),7) for x in normal],
        "offset_m":float(offset),
        "training_support_fraction_40mm":round(train_support,5),
        "training_robust_plane_span_5to95_m":[round(float(x),3) for x in (span[1]-span[0])],
        "candidate_training_inliers":int(len(inliers))
    }


def evaluate_plane(model, heldout_xyz):
    n=np.asarray(model["normal_xyz"],dtype=float)
    o=model["offset_m"]
    signed=heldout_xyz@n+o
    error=np.abs(signed)
    p=np.percentile(error,[50,90,95,99])*1000
    return {"heldout_points_unconditionally_evaluated":int(len(heldout_xyz)),
            "heldout_absolute_residual_mm_p50_p90_p95_p99":[round(float(x),3) for x in p],
            "heldout_signed_residual_median_mm":round(float(np.median(signed)*1000),3),
            "heldout_absolute_residual_rms_mm":round(float(np.sqrt(np.mean(error**2))*1000),3),
            "heldout_residual_over_40mm_pct":round(float(100*np.mean(error>.04)),3)}


def benchmark(frames, roi, sample_frames=12):
    validate_roi(roi)
    eligible=[i for i,f in enumerate(frames) if 170<=len(f)<=250]
    if len(eligible)<10:
        raise ValueError("need >=10 reasonably complete independent LiDAR frames")
    chosen=np.asarray(eligible)[np.linspace(0,len(eligible)-1,min(sample_frames,len(eligible)),dtype=int)]
    if len(set(chosen))<10:
        raise ValueError("insufficient distinct scans")
    xyz_list=[]; counts=[]
    for i in chosen:
        raw,xyz=qc.decode(frames[i])
        selected=select_roi(raw,xyz,roi)
        points=xyz[selected]
        counts.append(int(len(points)))
        xyz_list.append(points)
    mid=len(xyz_list)//2
    if min(counts)<150:
        raise ValueError("ROI too narrow or not observed in every training/heldout scan; sample counts="+repr(counts))
    train=np.concatenate(xyz_list[:mid],axis=0)
    hold=np.concatenate(xyz_list[mid:],axis=0)
    fit=fit_robust_plane(train)
    ev=evaluate_plane(fit,hold)
    frame_stats=[]
    for k,points in zip(chosen[mid:],xyz_list[mid:]):
        result=evaluate_plane(fit,points)
        frame_stats.append({"frame_index":int(k),
            "p95_unfiltered_mm":result["heldout_absolute_residual_mm_p50_p90_p95_p99"][2],
            "rms_unfiltered_mm":result["heldout_absolute_residual_rms_mm"]})
    return {"geometry_class":"ROI_ASSIGNED_BY_OPERATOR_NOT_INDEPENDENTLY_PROVEN",
            "surface_label":roi["surface_label"],
            "operator_has_verified_surface":roi.get("operator_has_verified_surface",False),
            "roi":roi,"frame_indices":chosen.astype(int).tolist(),
            "roi_points_per_frame":counts,
            "training_frames":mid,"heldout_frames":len(chosen)-mid,
            "train_plane":fit,"heldout":ev,"heldout_by_frame":frame_stats,
            "caveats":[
              "Plane is hypothesis fit to training ROI, not independent absolute metrology.",
              "Holdout residual is to that hypothesis without excluding outliers.",
              "Mixed geometry or wrong ROI will correctly inflate heldout errors.",
              "If rig moved during capture, fixed-plane temporal evaluation is invalid.",
              "No camera-lidar extrinsics, timestamps, calibrated range accuracy or edge truth."
            ]}


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--pcap",type=pathlib.Path,required=True)
    cli.add_argument("--roi-json",type=pathlib.Path,required=True)
    cli.add_argument("--output",type=pathlib.Path,required=True)
    cli.add_argument("--sample-frames",type=int,default=12)
    a=cli.parse_args()
    if not 10<=a.sample_frames<=40:
        raise ValueError("sample frame count must be in 10..40")
    roi=json.loads(a.roi_json.read_text())
    start=time.monotonic()
    frames=qc.load_pcap_frames(a.pcap)
    result=benchmark(frames,roi,a.sample_frames)
    result["pcap_sha256"]=hashlib.sha256(a.pcap.read_bytes()).hexdigest()
    result["config_sha256"]=hashlib.sha256(a.roi_json.read_bytes()).hexdigest()
    result["processing_s"]=round(time.monotonic()-start,3)
    result["provenance"]="READ_ONLY_PCAP_ORIGIN_NOT_EXTERNALLY_VERIFIED"
    a.output.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print(json.dumps({"report":str(a.output),
        "surface_label":result["surface_label"],
        "train_points":sum(result["roi_points_per_frame"][:result["training_frames"]]),
        "heldout_points":result["heldout"]["heldout_points_unconditionally_evaluated"],
        "heldout_p95_mm":result["heldout"]["heldout_absolute_residual_mm_p50_p90_p95_p99"][2],
        "wall_accuracy_certified":False},indent=2))


if __name__=="__main__":
    main()
