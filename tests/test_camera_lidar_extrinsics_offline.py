#!/usr/bin/env python3
"""Synthetic-only LiDAR->IMX252 optical PnP tests; no device/image access."""
import importlib.util
import pathlib
import unittest

import cv2
import numpy as np

PATH=pathlib.Path(__file__).resolve().parents[1]/"src"/"camera_lidar_extrinsics_offline.py"
spec=importlib.util.spec_from_file_location("pnp",PATH)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def fixture():
    rng=np.random.RandomState(2026)
    lidar=np.column_stack((rng.uniform(-.6,.6,48),
                           rng.uniform(1.6,4.0,48),
                           rng.uniform(-.4,.45,48)))
    rotation=np.array([[1.,0.,0.],[0.,0.,-1.],[0.,1.,0.]])
    t=np.array([.06,-.04,.12])
    rv,_=cv2.Rodrigues(rotation)
    k=np.array([[1200.,0.,1024.],[0.,1205.,768.],[0.,0.,1.]])
    dist=np.zeros(5)
    pixels,_=cv2.projectPoints(lidar,rv,t,k,dist)
    pixels=pixels.reshape(-1,2)+rng.normal(0,.15,(len(lidar),2))
    intrinsics={"status":"CAMERA_INTRINSICS_ONLY_NOT_LIDAR_CALIBRATION",
                 "size_px":[2048,1536],"camera_matrix":k.tolist(),
                 "distortion_coefficients":dist.tolist()}
    corrs={"source_class":"synthetic_fixture","pairs":[
       {"lidar_xyz_m":x.tolist(),"image_uv_px":u.tolist()}
       for x,u in zip(lidar,pixels)]}
    return intrinsics,corrs,rotation,t


class PnPTests(unittest.TestCase):
    def test_synthetic_3d_2d_transform_recovers_known_transform(self):
        intr,obs,true_r,true_t=fixture()
        out=module.solve(intr,obs)
        self.assertEqual(out["status"],"UNVERIFIED_CAMERA_LIDAR_EXTRINSIC_CANDIDATE_ONLY")
        self.assertLess(out["holdout_p95_reprojection_px"],1.5)
        np.testing.assert_allclose(out["rotation_R_camera_from_lidar"],true_r,atol=.03)
        np.testing.assert_allclose(out["translation_t_camera_from_lidar_m"],true_t,atol=.08)
        self.assertEqual(out["number_correspondences"],48)

    def test_cli_synthetic_json_roundtrip(self):
        import json
        import os
        import subprocess
        import sys
        import tempfile
        intr,obs,*_=fixture()
        with tempfile.TemporaryDirectory(prefix="synthetic_extrinsics_json_") as d:
            root=pathlib.Path(d)
            f1=root/"intrinsics.json";f2=root/"pairs.json";out=root/"result.json"
            f1.write_text(json.dumps(intr));f2.write_text(json.dumps(obs))
            run=subprocess.run([sys.executable,str(PATH),"--intrinsics",str(f1),
                 "--pairs",str(f2),"--output",str(out)],
                 capture_output=True,text=True,timeout=10,
                 env=dict(os.environ,OPENBLAS_NUM_THREADS="1",PYTHONDONTWRITEBYTECODE="1"))
            self.assertEqual(run.returncode,0,msg=run.stderr)
            result=json.loads(out.read_text())
            self.assertLess(result["holdout_p95_reprojection_px"],1.5)
            self.assertEqual(result["status"],"UNVERIFIED_CAMERA_LIDAR_EXTRINSIC_CANDIDATE_ONLY")

    def test_requires_provenance_and_intrinsic_input(self):
        intr,obs,*_=fixture()
        obs["source_class"]="invented_claim"
        with self.assertRaises(ValueError):
            module.solve(intr,obs)
        obs["source_class"]="synthetic_fixture"
        intr["status"]="NOT_CALIBRATED"
        with self.assertRaises(ValueError):
            module.solve(intr,obs)

    def test_invalid_correspondence_shapes_and_fov_fail_closed(self):
        intr,obs,*_=fixture()
        obs["pairs"][2]["image_uv_px"]=[99999.,99999.]
        with self.assertRaises(ValueError):
            module.solve(intr,obs)
        intr,obs,*_=fixture()
        obs["pairs"]=obs["pairs"][:5]
        with self.assertRaises(ValueError):
            module.solve(intr,obs)


if __name__=="__main__":
    unittest.main()
