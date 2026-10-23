#!/usr/bin/env python3
"""OFFLINE candidate LiDAR->camera optical rigid transform from verified correspondences.

Reads existing IMX252 intrinsic JSON and a user-authored list of LiDAR xyz metres
matched to pixel u,v. No image reading, sensor access, auto-correspondence or
unsupervised calibration claims. Spatial correspondence holdout is not
independent physical truth, clock synchronization or extrinsic certification.
"""
import argparse
import hashlib
import json
import pathlib

import cv2
import numpy as np


def validate_inputs(intrinsics, correspondences):
    if intrinsics.get("status")!="CAMERA_INTRINSICS_ONLY_NOT_LIDAR_CALIBRATION":
        raise ValueError("requires the intrinsic calibration output contract")
    k=np.asarray(intrinsics.get("camera_matrix"),dtype=np.float64)
    distortion=np.asarray(intrinsics.get("distortion_coefficients"),dtype=np.float64)
    width,height=intrinsics.get("size_px",[0,0])
    if k.shape!=(3,3) or len(distortion.reshape(-1)) not in (4,5,8,12,14):
        raise ValueError("invalid camera matrix/distortion")
    if not np.isfinite(k).all() or not np.isfinite(distortion).all() or k[0,0]<=0 or k[1,1]<=0:
        raise ValueError("nonfinite or invalid camera calibration")
    if width<100 or height<100:
        raise ValueError("missing verified camera image dimensions")
    label=correspondences.get("source_class")
    if label not in ("synthetic_fixture","operator_reviewed_real"):
        raise ValueError("correspondences must explicitly label synthetic or operator-reviewed source")
    rows=correspondences.get("pairs")
    if not isinstance(rows,list) or not 16<=len(rows)<=1000:
        raise ValueError("need 16..1000 explicitly matched 3D/2D pairs")
    world=np.asarray([r["lidar_xyz_m"] for r in rows],dtype=np.float64)
    pixels=np.asarray([r["image_uv_px"] for r in rows],dtype=np.float64)
    if world.shape!=(len(rows),3) or pixels.shape!=(len(rows),2):
        raise ValueError("invalid correspondence shape")
    if not np.isfinite(world).all() or not np.isfinite(pixels).all():
        raise ValueError("nonfinite 3D/2D measurement")
    if np.any((pixels[:,0]<0)|(pixels[:,0]>=width)|(pixels[:,1]<0)|(pixels[:,1]>=height)):
        raise ValueError("pixel coordinates outside calibration image")
    if np.ptp(world,axis=0).max()<.1:
        raise ValueError("physical 3D points insufficiently separated")
    rank=np.linalg.matrix_rank(world-world.mean(axis=0),tol=1e-4)
    if rank<2:raise ValueError("collinear 3D correspondences not accepted")
    return world,pixels,k,distortion,rank


def solve(intrinsics, correspondences, seed=23, pixel_thresh=3.):
    xyz,uv,k,dist,rank=validate_inputs(intrinsics,correspondences)
    if not 0.5<=pixel_thresh<=10:
        raise ValueError("RANSAC px threshold invalid")
    rng=np.random.RandomState(seed)
    shuffled=rng.permutation(len(xyz))
    holdout=max(4,int(round(len(xyz)*.25)))
    train_idx=shuffled[:-holdout]
    hold_idx=shuffled[-holdout:]
    cv2.setRNGSeed(seed)
    ok,rvec,tvec,inliers=cv2.solvePnPRansac(
        xyz[train_idx].astype(np.float64),uv[train_idx].astype(np.float64),
        k,dist,iterationsCount=1000,reprojectionError=pixel_thresh,
        confidence=.999,flags=cv2.SOLVEPNP_EPNP)
    if not ok or inliers is None or len(inliers)<8:
        raise RuntimeError("candidate extrinsics solve failed: too few RANSAC inliers")
    ix=train_idx[inliers.reshape(-1)]
    if hasattr(cv2,"solvePnPRefineLM"):
        rvec,tvec=cv2.solvePnPRefineLM(xyz[ix],uv[ix],k,dist,rvec,tvec)
    rotation,_=cv2.Rodrigues(rvec)
    optical_xyz=xyz@rotation.T+tvec.reshape(1,3)
    if np.min(optical_xyz[:,2])<=0:
        raise ValueError("solution places some measured points behind camera")
    pred,_=cv2.projectPoints(xyz[hold_idx],rvec,tvec,k,dist)
    error=np.linalg.norm(pred.reshape(-1,2)-uv[hold_idx],axis=1)
    pred_train,_=cv2.projectPoints(xyz[train_idx],rvec,tvec,k,dist)
    train_error=np.linalg.norm(pred_train.reshape(-1,2)-uv[train_idx],axis=1)
    T=np.eye(4);T[:3,:3]=rotation;T[:3,3]=tvec.reshape(3)
    return {"status":"UNVERIFIED_CAMERA_LIDAR_EXTRINSIC_CANDIDATE_ONLY",
            "input_class":correspondences["source_class"],
            "coordinate_convention":"p_camera_optical_m = R_camera_lidar @ p_lidar_m + t_camera_lidar_m",
            "transform_T_camera_optical_from_lidar":T.tolist(),
            "rotation_R_camera_from_lidar":rotation.tolist(),
            "translation_t_camera_from_lidar_m":tvec.reshape(-1).tolist(),
            "number_correspondences":len(xyz),
            "number_training_points":len(train_idx),
            "number_holdout_points":len(hold_idx),
            "training_ransac_inliers":len(ix),
            "training_p95_reprojection_px_all_points":round(float(np.percentile(train_error,95)),4),
            "holdout_p50_reprojection_px":round(float(np.percentile(error,50)),4),
            "holdout_p95_reprojection_px":round(float(np.percentile(error,95)),4),
            "holdout_rms_reprojection_px":round(float(np.sqrt(np.mean(error**2))),4),
            "training_source_3d_rank":int(rank),
            "limitations":[
                "Correspondences were user-supplied; optical camera and LiDAR frames are NOT measured as intrinsically synchronized.",
                "Spatial pair holdout checks internal consistency, NOT independently measured extrinsic truth.",
                "Planar/near-planar target geometry is pose-ambiguous; use diverse 3D target positions and independent sessions.",
                "Image pixel location must refer to the same resolution/mode as intrinsic calibration (native, not cropped preview).",
                "Physical calibration confirmation, independent target validation, drift testing, and sensor-time synchronization remain required."]}


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--intrinsics",type=pathlib.Path,required=True)
    cli.add_argument("--pairs",type=pathlib.Path,required=True)
    cli.add_argument("--output",type=pathlib.Path,required=True)
    a=cli.parse_args()
    d=json.loads(a.intrinsics.read_text())
    c=json.loads(a.pairs.read_text())
    result=solve(d,c)
    result["intrinsics_sha256"]=hashlib.sha256(a.intrinsics.read_bytes()).hexdigest()
    result["correspondences_sha256"]=hashlib.sha256(a.pairs.read_bytes()).hexdigest()
    a.output.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print(json.dumps({"status":result["status"],
        "correspondences":result["number_correspondences"],
        "holdout_p95_px":result["holdout_p95_reprojection_px"],
        "extrinsic_physically_certified":False},indent=2))


if __name__=="__main__":
    main()
