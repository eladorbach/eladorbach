#!/usr/bin/env python3
"""Offline IMX252 mono camera intrinsic calibration from voluntarily supplied images.

No device I/O, no image capture, no downloading, no saved pictures. The output
contains intrinsics, per-image SHA-256 provenance and residuals only. This
DOES NOT estimate the camera-to-LiDAR extrinsic transform or time offset.
"""
import argparse
import hashlib
import json
import pathlib
import time

import cv2
import numpy as np


def board_points(cols, rows, square_mm):
    """cols, rows are INNER corners, square_mm is measured center spacing."""
    if cols < 3 or rows < 3 or square_mm <= 0:
        raise ValueError("provide >=3x3 inner corners and positive measured square size")
    obj = np.zeros((cols*rows,3),dtype=np.float32)
    obj[:,:2] = np.mgrid[0:cols,0:rows].T.reshape(-1,2)*square_mm
    return obj


def find_corners(path, cols, rows):
    gray = cv2.imread(str(path),cv2.IMREAD_GRAYSCALE)
    if gray is None:
        raise ValueError("could not read image")
    if hasattr(cv2,"findChessboardCornersSB"):
        found,points=cv2.findChessboardCornersSB(gray,(cols,rows))
    else:
        found,points=cv2.findChessboardCorners(gray,(cols,rows))
        if found:
            term=(cv2.TERM_CRITERIA_EPS+cv2.TERM_CRITERIA_MAX_ITER,40,.001)
            points=cv2.cornerSubPix(gray,points,(9,9),(-1,-1),term)
    if not found:
        return gray.shape[::-1],None
    return gray.shape[::-1],points.astype(np.float32)


def solve_from_points(obj_list,img_list,size,holdout_count):
    """Fit lens from train images only; pose fit on held-out target observations."""
    if len(obj_list) != len(img_list) or len(obj_list) < 10:
        raise ValueError("requires at least ten verified diverse target views")
    if holdout_count < 2 or holdout_count >= len(obj_list)-5:
        raise ValueError("holdout_count must be >=2 and leave six training views")
    train=len(obj_list)-holdout_count
    err,k,dist,rvecs,tvecs=cv2.calibrateCamera(
        obj_list[:train],img_list[:train],size,None,None,
        criteria=(cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER,100,1e-9))
    train_res=[]
    for obj,obs,r,t in zip(obj_list[:train],img_list[:train],rvecs,tvecs):
        pred,_=cv2.projectPoints(obj,r,t,k,dist)
        train_res.extend(np.linalg.norm(pred.reshape(-1,2)-obs.reshape(-1,2),axis=1).tolist())
    heldout_res=[]
    for obj,obs in zip(obj_list[train:],img_list[train:]):
        ok,r,t=cv2.solvePnP(obj,obs,k,dist,flags=cv2.SOLVEPNP_ITERATIVE)
        if not ok:
            raise RuntimeError("held-out pose solve failed")
        pred,_=cv2.projectPoints(obj,r,t,k,dist)
        heldout_res.extend(np.linalg.norm(pred.reshape(-1,2)-obs.reshape(-1,2),axis=1).tolist())
    return {"model":"opencv_pinhole_brown_conrady_default", "size_px":list(size),
            "camera_matrix":k.tolist(),"distortion_coefficients":dist.reshape(-1).tolist(),
            "train_images":train,"holdout_images":holdout_count,
            "opencv_fit_rms_px":float(err),
            "train_corner_p50_px":float(np.percentile(train_res,50)),
            "train_corner_p95_px":float(np.percentile(train_res,95)),
            "heldout_corner_p50_px":float(np.percentile(heldout_res,50)),
            "heldout_corner_p95_px":float(np.percentile(heldout_res,95)),
            "holdout_limitation":("Each hold-out image pose is solved using its own target corners. "
                "This checks calibration consistency but is NOT independent physical metrology "
                "or validation of the M1600/IMX252 extrinsic transform.")}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--images",type=pathlib.Path,required=True)
    p.add_argument("--inner-cols",type=int,required=True)
    p.add_argument("--inner-rows",type=int,required=True)
    p.add_argument("--square-mm",type=float,required=True)
    p.add_argument("--output",type=pathlib.Path,required=True)
    p.add_argument("--holdout-images",type=int,default=3)
    a=p.parse_args()
    obj=board_points(a.inner_cols,a.inner_rows,a.square_mm)
    formats={".png",".jpg",".jpeg",".tif",".tiff"}
    paths=sorted((x for x in a.images.iterdir() if x.is_file() and x.suffix.lower() in formats),key=lambda x:x.name)
    if not 10<=len(paths)<=60:
        raise ValueError("expected 10 to 60 user-reviewed target images; no automatic capture")
    xyz=[];corners=[];digest=[];image_size=None;rejected=0
    for path in paths:
        size,im=find_corners(path,a.inner_cols,a.inner_rows)
        if image_size is None:image_size=size
        elif size!=image_size:raise ValueError("mixed image dimensions")
        if im is None:
            rejected+=1
            continue
        xyz.append(obj.copy())
        corners.append(im)
        h=hashlib.sha256()
        with path.open("rb") as stream:
            for part in iter(lambda:stream.read(1024*1024),b""):
                h.update(part)
        digest.append(h.hexdigest())
    if len(corners)<10:raise ValueError("fewer than ten detectable board views")
    summary=solve_from_points(xyz,corners,image_size,a.holdout_images)
    summary.update({"status":"CAMERA_INTRINSICS_ONLY_NOT_LIDAR_CALIBRATION",
        "camera_type":"monochrome_IMX252_user_supplied",
        "inner_corners":[a.inner_cols,a.inner_rows],
        "square_mm":a.square_mm,"detected_images":len(corners),
        "rejected_images":rejected,
        "sha256_in_sorted_accepted_image_order":digest,
        "opencv_version":cv2.__version__,
        "warnings":["Check image exposure and corner distribution; no autofocus/zoom changes across frames",
            "Actual lens and shutter/exposure configuration must be documented",
            "Raw calibration images are not stored or copied by this tool",
            "Physical target measurements and independent verification are required",
            "No sensor timestamps, IMU poses, or camera-to-LiDAR transform are available"]})
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(summary,indent=2)+"\n")
    print("INTRINSICS_ONLY",len(corners),"images","heldout_p95_px",round(summary["heldout_corner_p95_px"],3))


if __name__=="__main__":
    main()
