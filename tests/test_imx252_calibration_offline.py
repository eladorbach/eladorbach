#!/usr/bin/env python3
"""Synthetic-only camera calibration tests: no human imagery or camera interaction."""
import importlib.util
import pathlib
import unittest

import cv2
import numpy as np

PATH=pathlib.Path(__file__).resolve().parents[1]/"src"/"imx252_calibration_offline.py"
spec=importlib.util.spec_from_file_location("offline_calibration",PATH)
cal=importlib.util.module_from_spec(spec)
spec.loader.exec_module(cal)


class CalibrationMathTests(unittest.TestCase):
    def test_board_geometry(self):
        p=cal.board_points(9,6,20.0)
        self.assertEqual(p.shape,(54,3))
        np.testing.assert_array_equal(p[0],[0,0,0])
        self.assertAlmostEqual(np.linalg.norm(p[1,:2]-p[0,:2]),20)
        self.assertTrue(np.allclose(p[:,2],0))

    def test_invalid_target(self):
        with self.assertRaises(ValueError):
            cal.board_points(9,6,0)
        with self.assertRaises(ValueError):
            cal.board_points(2,6,20)

    def test_calibration_solver_on_synthetic_projections(self):
        board=cal.board_points(9,6,20.0)
        k=np.array([[1210.,0,1024.],[0,1220.,768.],[0,0,1.]])
        distortion=np.array([.02,-.04,.0004,-.0001,.008])
        obj=[];views=[]
        for i in range(14):
            rvec=np.array([.08+0.025*i,-.16+0.03*i,.014*i],dtype=float)
            tvec=np.array([-100+14*i,-60+9*i,800+31*i],dtype=float)
            uv,_=cv2.projectPoints(board,rvec,tvec,k,distortion)
            obj.append(board.copy());views.append(uv.astype('f4'))
        fitted=cal.solve_from_points(obj,views,(2048,1536),3)
        self.assertEqual(fitted["train_images"],11)
        self.assertEqual(fitted["holdout_images"],3)
        self.assertLess(fitted["heldout_corner_p95_px"],1.0)
        self.assertEqual(len(fitted["camera_matrix"]),3)

    def test_reject_uninspected_low_view_count(self):
        board=cal.board_points(9,6,20.)
        with self.assertRaises(ValueError):
            cal.solve_from_points([board]*5,[board[:,:2].reshape(54,1,2)]*5,(2048,1536),2)


if __name__=="__main__":
    unittest.main()
