# AGX multimodal mobile 3D reconstruction — publication workspace
**Public-release candidate only. Nothing here is a claim of completed mapping or fusion.**

Our engineering challenge is to produce smooth, accurate, inspectable indoor 3D surfaces from independently verified measurements, while preserving actual edges, detecting reflective/multipath artifacts, and transparently separating measured from inferred geometry.

- [Eight-month 2026 research survey](RESEARCH_20260222_TO_20261022.md)
- [Operator-ready execution and measurement roadmap](EXECUTION_ROADMAP_20261022.md)
- [Next experiment: measured wall, floor and corner](NEXT_WALL_FLOOR_EXPERIMENT.md)
- [Research goals / validity criteria](PROJECT_CHARTER_20261022.md)
- [Side-by-side sensor evaluation and safe bring-up](SENSOR_BENCH_MATRIX_20261022.md)
- [LinkedIn story, figures, measurement tables, and GitHub release gates](PUBLICATION_PLAN_20261022.md)

**Verified baseline:** authentic live M1600 PointCloud2 plus monochrome IMX252 preview on one AGX HDMI RViz session; native IMX250 PolarSens and other LiDARs not yet fused. M1600 packet decoder structure/software math has been cross-checked against 11,752 returns from an immutable real capture. Physical metrological accuracy remains unverified.

**Not built:** calibrated camera-LiDAR fusion, synchronized IMU odometry, mobile SLAM, optical polarization fusion, denser mapped surfaces, Gaussian splatting.

**License/privacy:** This research branch contains original experiment documentation and self-authored offline testing scripts. No external license has yet been selected. Never add raw PCAPs, camera imagery, passwords, sensor-unique MAC identifiers, local sensor identity JSON, private Waymo SDKs or third-party code without publication-rights review.

**Publication:** This is an independent research and measurement-tools branch inside the existing eladorbach/eladorbach repository, intentionally separate from deployed main. It does **not** announce completed fusion, mobile reconstruction, verified wall accuracy, or camera-LiDAR calibration.

## October 23 prepared **portable-rig test-day workflow**

- [Step-by-step full-wall, corner, camera and synchronization test plan](TEST_DAY_READINESS_20261023.md)
- [Safe source-verified live M1600 capture](src/m1600_capture_verified.py)
- [One-command LiDAR multi-trial session runner](src/m1600_test_session.py)
- [Predeclared full-wall ROI held-out benchmark](src/full_wall_benchmark.py)
- [Quality/acceptance gate: fail unsafe/uncontrolled scenes](src/m1600_session_gate.py)
- [Independent two-plane/corner analysis](src/corner_benchmark.py)
- [Full-wall ROI template, not yet physically verified](examples/full_wall_roi_TEMPLATE.json)

These modules were checked on the AGX with real sensor packets and synthetic
regression fixtures. Operator-selected physical wall/floor/corner targets,
extrinsics and absolute metrology remain pending the user's portable rig.
All raw captures, unique LiDAR identifiers and numerical reports remain private.

## 2026-10-23 offline tools and actual evidence
- [October 23 measured progress and limitations](PROGRESS_20261023.md)
- [M1600 offline quality tool](src/m1600_offline_qc.py): raw-PCAP decoder, 16-channel consistency, temporal held-out comparison and a depth-edge **risk flag**. Does not modify the live cloud.
- [IMX252 camera intrinsic calibration](src/imx252_calibration_offline.py): future, user-supplied checkerboard images only; no auto-capture, no camera-LiDAR extrinsics yet.
- [Live ROS subscriber quality probe](src/live_ros_rate_probe.py): reads ROS message metadata, does not save image pixels.
- [Regression tests](tests/): exclusively labeled synthetic fixtures; nothing from a private scene.

Reproduce using an authorized genuine M1600 PCAP on the AGX:
```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -v -s tests
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 python3 src/m1600_offline_qc.py --pcap /path/to/your/M1600.pcap --bin-centidegrees 10
```
**Caveat:** Reduced cross-frame range disagreement is NOT verified physical wall flatness. No images, raw packets, private room scans, or vendor SDKs are part of this publication branch.
